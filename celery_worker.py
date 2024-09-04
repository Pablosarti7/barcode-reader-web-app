from celery import Celery # type: ignore
from ingredients_api import get_all_ingredients, get_ingredient, add_ingredient
import os

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
celery = Celery('tasks', broker=redis_url, backend=redis_url)

@celery.task
def async_get_all_ingredients():
    return get_all_ingredients()

@celery.task
def async_get_ingredient(ingredient):
    return get_ingredient(ingredient)

@celery.task
def async_add_ingredient(ingredients):
    return add_ingredient(ingredients)