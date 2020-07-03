from faker import Faker
from pytest import fixture


@fixture(autouse=True)
def fake():
    yield Faker()
