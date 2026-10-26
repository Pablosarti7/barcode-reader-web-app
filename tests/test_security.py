from unittest.mock import Mock, patch

import pytest
from flask import Flask

from config import configure_app
from main import app, db, Users, ScanHistory


@pytest.fixture
def accounts():
    with app.app_context():
        owner = Users(name='Owner', email='owner@example.com', customer_id='cus_owner')
        other = Users(name='Other', email='other@example.com', customer_id='cus_other')
        db.session.add_all([owner, other])
        db.session.flush()
        item = ScanHistory(user_id=owner.id, item_name='Food', item_barcode='013000626095')
        db.session.add(item)
        db.session.commit()
        return owner.id, other.id, item.id


def sign_in(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


def subscription(status='active', subscription_id='sub_owner'):
    return {'id': subscription_id, 'customer': 'cus_owner', 'status': status,
            'items': {'data': [{'price': {'lookup_key': 'big_monthly'}}]}}


@pytest.mark.parametrize('identity,expected', [('anonymous', 302), ('other', 404), ('owner', 302)])
def test_delete_requires_ownership(client, post, accounts, identity, expected):
    owner, other, item_id = accounts
    if identity != 'anonymous':
        sign_in(client, owner if identity == 'owner' else other)
    response = post(f'/delete/{item_id}')
    assert response.status_code == expected
    with app.app_context():
        assert (db.session.get(ScanHistory, item_id) is None) == (identity == 'owner')


def test_delete_rejects_get_and_missing_csrf(client, accounts):
    owner, _, item_id = accounts
    sign_in(client, owner)
    assert client.get(f'/delete/{item_id}').status_code == 405
    assert client.post(f'/delete/{item_id}').status_code == 400
    with app.app_context():
        assert db.session.get(ScanHistory, item_id) is not None


@pytest.mark.parametrize('path', ['/create-checkout-session', '/create-portal-session', '/logout'])
def test_sensitive_posts_require_login(client, post, path):
    with patch('main.stripe.checkout.Session.create') as checkout, \
         patch('main.stripe.billing_portal.Session.create') as portal:
        assert post(path).status_code == 302
        checkout.assert_not_called()
        portal.assert_not_called()


def test_settings_requires_login(client):
    assert client.get('/settings').status_code == 302


def test_portal_ignores_browser_supplied_checkout_session(client, post, accounts, monkeypatch):
    sign_in(client, accounts[0])
    monkeypatch.setattr('main.stripe.api_key', 'sk_test_placeholder')
    with patch('main.stripe.billing_portal.Session.create', return_value=Mock(url='https://billing.stripe.com/test')) as portal, \
         patch('main.stripe.checkout.Session.retrieve') as checkout:
        response = post('/create-portal-session', {'session_id': 'someone-elses-checkout'})
    assert response.status_code == 303
    assert portal.call_args.kwargs['customer'] == 'cus_owner'
    checkout.assert_not_called()


def test_portal_requires_server_customer(client, post, accounts, monkeypatch):
    sign_in(client, accounts[0])
    monkeypatch.setattr('main.stripe.api_key', 'sk_test_placeholder')
    with app.app_context():
        db.session.get(Users, accounts[0]).customer_id = None
        db.session.commit()
    with patch('main.stripe.billing_portal.Session.create') as portal:
        assert post('/create-portal-session').status_code == 409
        portal.assert_not_called()


def test_checkout_binds_user_and_customer(client, post, accounts, monkeypatch):
    sign_in(client, accounts[0])
    monkeypatch.setattr('main.stripe.api_key', 'sk_test_placeholder')
    with patch('main.stripe.Price.list', return_value=Mock(data=[Mock(id='price_big')])), \
         patch('main.stripe.checkout.Session.create', return_value=Mock(url='https://checkout.stripe.com/test')) as checkout:
        response = post('/create-checkout-session', {'lookup_key': 'big_monthly'})
    assert response.status_code == 303
    assert checkout.call_args.kwargs['customer'] == 'cus_owner'
    assert checkout.call_args.kwargs['client_reference_id'] == str(accounts[0])
    assert checkout.call_args.kwargs['success_url'] == app.config['PUBLIC_BASE_URL'] + '/success'


def test_checkout_creates_and_stores_customer(client, post, accounts, monkeypatch):
    sign_in(client, accounts[0])
    monkeypatch.setattr('main.stripe.api_key', 'sk_test_placeholder')
    with app.app_context():
        db.session.get(Users, accounts[0]).customer_id = None
        db.session.commit()
    with patch('main.stripe.Price.list', return_value=Mock(data=[Mock(id='price_big')])), \
         patch('main.stripe.Customer.create', return_value=Mock(id='cus_new')) as customer, \
         patch('main.stripe.checkout.Session.create', return_value=Mock(url='https://checkout.stripe.com/test')) as checkout:
        assert post('/create-checkout-session', {'lookup_key': 'big_monthly'}).status_code == 303
    with app.app_context():
        assert db.session.get(Users, accounts[0]).customer_id == 'cus_new'
    assert customer.call_args.kwargs['metadata']['user_id'] == str(accounts[0])
    assert checkout.call_args.kwargs['customer'] == 'cus_new'


def test_checkout_rejects_unknown_plan(client, post, accounts, monkeypatch):
    sign_in(client, accounts[0])
    monkeypatch.setattr('main.stripe.api_key', 'sk_test_placeholder')
    with patch('main.stripe.Price.list') as prices:
        assert post('/create-checkout-session', {'lookup_key': 'unexpected'}).status_code == 400
        prices.assert_not_called()


@pytest.mark.parametrize('status,show_history', [('active', True), ('trialing', True), ('canceled', False), ('past_due', False)])
def test_history_requires_active_subscription(client, accounts, status, show_history):
    sign_in(client, accounts[0])
    with app.app_context():
        db.session.get(Users, accounts[0]).subscription_id = 'sub_owner'
        db.session.commit()
    with patch('main.stripe.Subscription.retrieve', return_value=subscription(status)):
        response = client.get('/settings?section=scan_history')
    assert response.status_code == 200
    assert (b'013000626095' in response.data) == show_history


def test_webhook_requires_configuration(client, monkeypatch):
    monkeypatch.setitem(app.config, 'STRIPE_WEBHOOK_SECRET', None)
    assert client.post('/webhook', json={}).status_code == 503


def test_webhook_rejects_invalid_signature(client, accounts):
    import stripe
    with patch('main.stripe.Webhook.construct_event', side_effect=stripe.SignatureVerificationError('Invalid', 'bad')):
        assert client.post('/webhook', data='{}', headers={'Stripe-Signature': 'bad'}).status_code == 400
    with app.app_context():
        assert db.session.get(Users, accounts[0]).subscription_id is None


def test_webhook_checks_real_signature(client, accounts):
    """Exercise Stripe's verifier, including the CSRF exemption and raw payload."""
    import hashlib
    import hmac
    import json
    import time
    payload = json.dumps({'type': 'checkout.session.completed', 'data': {'object': {
        'customer': 'cus_owner', 'client_reference_id': str(accounts[0]),
        'mode': 'subscription', 'subscription': 'sub_owner'}}})
    timestamp = int(time.time())
    digest = hmac.new(b'test-webhook-secret', f'{timestamp}.{payload}'.encode(), hashlib.sha256).hexdigest()
    with patch('main.stripe.Subscription.retrieve', return_value=subscription()):
        response = client.post('/webhook', data=payload, headers={'Stripe-Signature': f't={timestamp},v1={digest}'})
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Users, accounts[0]).subscribed is True
    assert client.post('/webhook', data=payload + ' ', headers={'Stripe-Signature': f't={timestamp},v1={digest}'}).status_code == 400


@pytest.mark.parametrize('event_type,status', [('checkout.session.completed', 'active'), ('customer.subscription.updated', 'past_due'), ('customer.subscription.deleted', 'canceled')])
def test_webhook_sync_is_idempotent(client, accounts, event_type, status):
    obj = {'id': 'sub_owner', 'customer': 'cus_owner', 'subscription': 'sub_owner',
           'mode': 'subscription', 'client_reference_id': str(accounts[0])}
    event = {'type': event_type, 'data': {'object': obj}}
    with patch('main.stripe.Webhook.construct_event', return_value=event), \
         patch('main.stripe.Subscription.retrieve', return_value=subscription(status)):
        for _ in range(2):
            assert client.post('/webhook', data='{}').status_code == 200
    with app.app_context():
        user = db.session.get(Users, accounts[0])
        assert user.subscription_id == 'sub_owner'
        assert user.subscribed == (status == 'active')


def test_old_subscription_event_cannot_overwrite_new_subscription(client, accounts):
    with app.app_context():
        user = db.session.get(Users, accounts[0])
        user.subscription_id = 'sub_new'
        user.subscribed = True
        db.session.commit()
    event = {'type': 'customer.subscription.deleted', 'data': {'object': {'id': 'sub_old', 'customer': 'cus_owner'}}}
    with patch('main.stripe.Webhook.construct_event', return_value=event), \
         patch('main.stripe.Subscription.retrieve') as retrieve:
        assert client.post('/webhook', data='{}').json['status'] == 'ignored'
        retrieve.assert_not_called()
    with app.app_context():
        assert db.session.get(Users, accounts[0]).subscribed is True


def test_checkout_webhook_cannot_link_another_user(client, accounts):
    event = {'type': 'checkout.session.completed', 'data': {'object': {
        'customer': 'cus_owner', 'client_reference_id': str(accounts[1]),
        'mode': 'subscription', 'subscription': 'sub_other'}}}
    with patch('main.stripe.Webhook.construct_event', return_value=event), \
         patch('main.stripe.Subscription.retrieve') as retrieve:
        assert client.post('/webhook', data='{}').json['status'] == 'ignored'
        retrieve.assert_not_called()


def test_session_cookie_survives_app_restart(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'persistent-test-key')
    apps = [Flask('first'), Flask('second')]
    for instance in apps:
        configure_app(instance)
    serializer = apps[0].session_interface.get_signing_serializer(apps[0])
    cookie = serializer.dumps({'_user_id': '42'})
    assert apps[1].session_interface.get_signing_serializer(apps[1]).loads(cookie)['_user_id'] == '42'


def test_production_requires_configuration(monkeypatch):
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        configure_app(Flask('missing-secret'))
    monkeypatch.setenv('SECRET_KEY', 'production-test-key')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        configure_app(Flask('missing-database'))
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    production = Flask('production')
    configure_app(production)
    assert production.config['SESSION_COOKIE_SECURE'] is True
    assert production.config['REMEMBER_COOKIE_SECURE'] is True


def test_init_db_refuses_production(monkeypatch):
    monkeypatch.setitem(app.config, 'DEVELOPMENT', False)
    result = app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code != 0
    assert 'local development only' in result.output


def test_delayed_checkout_cannot_replace_new_active_subscription(client, accounts):
    with app.app_context():
        user = db.session.get(Users, accounts[0])
        user.subscription_id = 'sub_new'
        user.subscribed = True
        db.session.commit()
    event = {'type': 'checkout.session.completed', 'data': {'object': {
        'customer': 'cus_owner', 'client_reference_id': str(accounts[0]),
        'mode': 'subscription', 'subscription': 'sub_old'}}}
    with patch('main.stripe.Webhook.construct_event', return_value=event), \
         patch('main.stripe.Subscription.retrieve', side_effect=[subscription('canceled', 'sub_old'), subscription('active', 'sub_new')]):
        assert client.post('/webhook', data='{}').json['status'] == 'ignored'
    with app.app_context():
        assert db.session.get(Users, accounts[0]).subscription_id == 'sub_new'
        assert db.session.get(Users, accounts[0]).subscribed is True


def test_checkout_can_replace_canceled_subscription(client, accounts):
    with app.app_context():
        user = db.session.get(Users, accounts[0])
        user.subscription_id = 'sub_old'
        user.subscribed = False
        db.session.commit()
    event = {'type': 'checkout.session.completed', 'data': {'object': {
        'customer': 'cus_owner', 'client_reference_id': str(accounts[0]),
        'mode': 'subscription', 'subscription': 'sub_new'}}}
    with patch('main.stripe.Webhook.construct_event', return_value=event), \
         patch('main.stripe.Subscription.retrieve', side_effect=[subscription('active', 'sub_new'), subscription('canceled', 'sub_old')]):
        assert client.post('/webhook', data='{}').json['status'] == 'success'
    with app.app_context():
        assert db.session.get(Users, accounts[0]).subscription_id == 'sub_new'
        assert db.session.get(Users, accounts[0]).subscribed is True


@pytest.mark.parametrize('path,data', [('/', {'barcode': '013000626095'}), ('/create-checkout-session', {'lookup_key': 'big_monthly'}), ('/create-portal-session', {})])
def test_browser_posts_reject_missing_csrf(client, accounts, path, data):
    sign_in(client, accounts[0])
    assert client.post(path, data=data).status_code == 400


def test_camera_and_checkout_forms_have_csrf(client):
    from html.parser import HTMLParser
    class FormParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []
            self.current = None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'form':
                self.current = {'post': attrs.get('method', '').upper() == 'POST', 'token': False}
                self.forms.append(self.current)
            elif tag == 'input' and self.current is not None and attrs.get('name') == 'csrf_token':
                self.current['token'] = bool(attrs.get('value'))
        def handle_endtag(self, tag):
            if tag == 'form':
                self.current = None
    for path in ['/', '/search', '/pricing']:
        parser = FormParser()
        parser.feed(client.get(path).data.decode())
        assert all(form['token'] for form in parser.forms if form['post'])


@pytest.mark.parametrize('barcode', ['', 'not-a-barcode', '12345'])
def test_invalid_barcode_never_calls_upstream(client, post, barcode):
    with patch('main.get_product_info') as lookup:
        assert post('/', {'barcode': barcode}).status_code == 400
        lookup.assert_not_called()
