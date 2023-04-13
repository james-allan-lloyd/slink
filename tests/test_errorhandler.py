import pytest
from requests.exceptions import HTTPError
from responses import RequestsMock
from slink.api import Api
from slink.decorators import get
from tests.support import DEFAULT_BASE_URL


def test_error_handler(mocked_responses: RequestsMock):
    base_url = DEFAULT_BASE_URL
    mocked_responses.get(
        f"{base_url}/rest/api/3",
        json={"error": "not found"},
        status=404,
    )

    class TestApi(Api):
        @get("rest/api/3")
        def get_api(self, my_arg: str):
            return self.response.json()

        def check_response(self):
            self.response.raise_for_status()

    api = TestApi(base_url=DEFAULT_BASE_URL)
    with pytest.raises(HTTPError) as e:
        api.get_api(my_arg="some_arg")
