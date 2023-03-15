import pytest
import responses

from slink import Api, put, Body
from support import DEFAULT_BASE_URL


def test_put_makes_requests(
    mocked_responses: responses.RequestsMock,
):
    resource_key = "test_resource"
    base_url = DEFAULT_BASE_URL

    class TestApi(Api):
        @put("/resources/{my_resource}", updates=Body())
        def update_resource(self, my_resource: str, updates: dict):
            self.response.raise_for_status()

    updates = {"test": {"name": "first", "type": "json"}}
    post_method = mocked_responses.put(
        f"{base_url}/resources/{resource_key}",
        match=[responses.matchers.json_params_matcher(updates)],
    )

    api = TestApi(base_url=base_url)
    api.update_resource(my_resource=resource_key, updates=updates)

    assert post_method.call_count == 1


def test_put_raises_exception_for_multiple_json_body():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @put("rest/api/3", body=Body(), body2=Body())
            def post_resource(self, resource_key: str, body: dict, body2: dict):
                pass

    assert "Can only have one Body() argument to @put" in str(e)
