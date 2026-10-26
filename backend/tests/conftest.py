import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def reset_rate_limits():
    cache.clear()


@pytest.fixture
def client():
    return APIClient()
