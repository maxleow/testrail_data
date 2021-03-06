import os
from pathlib import Path
import pytest

from testrail_data import TestRailAPI

BASE_HOST = 'https://example.testrail.com/index.php?/api/v2/'


@pytest.fixture(scope='session')
def host():
    yield 'https://example.testrail.com/'


@pytest.fixture(scope='session')
def base_path():
    path = Path(__file__).absolute().parent
    yield str(path)


@pytest.fixture(scope='session')
def auth_data(host):
    yield host, 'example@mail.com', 'password'


@pytest.fixture
def api(auth_data):
    api = TestRailAPI(*auth_data)
    yield api


@pytest.fixture
def environ(auth_data):
    os.environ['TESTRAIL_URL'] = auth_data[0]
    os.environ['TESTRAIL_EMAIL'] = auth_data[1]
    os.environ['TESTRAIL_PASSWORD'] = auth_data[2]
    yield
    del os.environ['TESTRAIL_URL']
    del os.environ['TESTRAIL_EMAIL']
    del os.environ['TESTRAIL_PASSWORD']
