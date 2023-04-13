import responses
import pytest


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def strict_mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        yield rsps
