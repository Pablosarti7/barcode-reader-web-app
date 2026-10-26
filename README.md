# Ingredient Advisor

A Flask web app for scanning food barcodes, looking up ingredients, and saving scan history. The frontend uses Jinja templates, Tailwind CSS, and a browser camera scanner.

Development branch: **`improve/security-and-local-setup`**. Work on this branch stays separate from `main` until its pull request is merged.

## 1. Get the repository into VS Code

Install [Git](https://git-scm.com/downloads), [Python 3.12](https://www.python.org/downloads/), [Node.js 22 LTS](https://nodejs.org/), and [VS Code](https://code.visualstudio.com/). On Windows, enable Python's **Add Python to PATH** option during installation. In VS Code, install Microsoft's **Python** extension.

For your first download, open a terminal in the folder where you keep projects:

```sh
git clone --branch improve/security-and-local-setup https://github.com/Pablosarti7/barcode-reader-web-app.git
cd barcode-reader-web-app
code .
```

If `code .` is unavailable, open VS Code and choose **File → Open Folder**, then select `barcode-reader-web-app`.

If you already have a clone, open that folder in VS Code and use **Terminal → New Terminal**:

```sh
git status
git fetch origin
git switch --track origin/improve/security-and-local-setup
```

If this branch already exists locally, use `git switch improve/security-and-local-setup` instead. If `git status` lists work you haven't saved in a commit, keep it before switching; do not discard it.

For your macOS setup, use the **macOS or Linux** commands below. Keep this guide open beside the VS Code terminal.

## 2. Create a Python environment

A virtual environment keeps this project's Python packages separate from other projects. Run these commands from the repository folder.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, select **Command Prompt** from the VS Code terminal dropdown and run `.venv\Scripts\activate.bat`. You can also skip activation and use `.\.venv\Scripts\python.exe` instead of `python` in subsequent commands.

**macOS or Linux:**

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

On some Linux distributions, you may need to install the Python venv package first. In VS Code, open the Command Palette, choose **Python: Select Interpreter**, and select the interpreter inside `.venv`.

**Both platforms, with the environment active:**

```sh
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
npm ci
npm run build:css
```

## 3. Configure a local app

Copy `.env.example` to `.env` using VS Code's file explorer. Alternatively:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```sh
# macOS/Linux
cp .env.example .env
```

Generate a session secret:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output after `SECRET_KEY=` in `.env`. Keep `APP_ENV=development` and leave `DATABASE_URL` blank. This uses a separate SQLite file in `instance/ingredient_advisor.db`, not your hosted database. Do not put a production database URL in your local `.env`.

The app can start without Google, Stripe, mail, or OpenAI credentials. Signing in requires Google credentials; analyzing an uncached product requires OpenAI and the external enrichment services. Looking up ingredients and scanning products still depend on the external food APIs. The automated tests mock these services, so tests do not require credentials or Internet access after dependencies are installed.

## 4. Initialize and run

```sh
python -m flask --app main init-db
python -m flask --app main run --debug
```

Open **http://127.0.0.1:5000**. The initialization command creates missing local tables without deleting existing records. It is disabled outside development. Stop the server with **Ctrl+C**.

Check the home, About, Search, and Pricing pages first. Google login will explain that it needs configuration if credentials are absent. An existing cached product can be looked up without OpenAI; a new product needs the optional integrations above.

Browser camera access works on localhost. Testing the camera on your phone through your computer's LAN address generally requires HTTPS; desktop localhost testing does not provide a phone-accessible HTTPS site.

## 5. Run automated tests

```sh
python -m pytest -q
```

Tests use a temporary in-memory SQLite database, real CSRF validation, mocked external HTTP calls, and no production credentials. They cover browsing, Google callbacks, barcode results, history ownership, billing customer binding, signed webhooks, and session configuration.

You can run tests in VS Code too: choose **Python: Configure Tests**, select **pytest**, then choose `tests`. Use the Testing sidebar to run or debug them.

## 6. Next time you work on the app

Open the folder in VS Code, activate `.venv` again, then:

```sh
git status
git switch improve/security-and-local-setup
git pull --ff-only origin improve/security-and-local-setup
python -m pip install -r requirements-dev.txt
npm ci
npm run build:css
python -m flask --app main run --debug
```

`git clone` downloads the project the first time. `git pull` gets later updates. If Git reports local changes or divergent commits, stop and keep your work; do not use a hard reset to force an update.

## Optional integrations

- **Google login:** set `CLIENT_ID` and `CLIENT_SECRET` from a Google OAuth web client. Register `http://127.0.0.1:5000/callback` as an authorized redirect URI and add your Google account as a test user when required. Use the same hostname in the browser and redirect URI.
- **Food enrichment:** set `OPENAI_API_KEY`, the ingredient service's `SECRET_API_KEY`, and the product service's `PRODUCTS_API_KEY`. Keys must belong to those services. AI calls may incur usage charges. Ingredient scoring and recommendation quality still need further work.
- **Stripe:** use test-mode keys and recurring prices with lookup keys `small_monthly` and `big_monthly`. Configure checkout-completion and subscription created/updated/deleted webhook events. For local testing, the Stripe CLI can forward events with `stripe listen --forward-to http://127.0.0.1:5000/webhook`; put its signing secret in `STRIPE_WEBHOOK_SECRET`, then restart Flask. Complete checkout through this app while signed in so the customer is linked to your local account. Random CLI fixture customers will be ignored. The portal always uses the authenticated account's stored customer ID.

Never commit `.env` or paste credentials into a pull request. `.env` and the local SQLite database are ignored by Git.

## Before deploying this branch

- Set a persistent, private `SECRET_KEY`, the existing production `DATABASE_URL`, `PUBLIC_BASE_URL`, and required integration credentials. Leave `APP_ENV` unset or set it to `production`; only the explicit `development` value permits HTTP cookies and a local database fallback.
- Rotate the Stripe webhook signing secret previously embedded in the source, configure the replacement as `STRIPE_WEBHOOK_SECRET`, and ensure Stripe sends the events listed above. Webhooks reject requests when the secret is missing or the signature is invalid.
- Preserve existing Stripe customer/subscription associations. Legacy accounts that never stored a customer ID need a verified reconciliation before portal access can work; do not associate accounts using browser-supplied checkout IDs.
- This change uses the existing database columns and requires no schema migration. The development `init-db` command is not a production migration tool.
- Deploy a preview and check real Google and Stripe test-mode flows before switching production. Use HTTPS and a production WSGI server (`gunicorn main:app`); do not expose Flask's debug server.

The interface and broader backend refactor are subsequent stages. Account deletion remains unimplemented and must not be presented as a successful deletion.
