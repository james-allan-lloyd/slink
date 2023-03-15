import pytest
import responses

from slink import Api, delete
from slink.api import Body
from support import DEFAULT_BASE_URL


def test_delete_makes_requests(
    mocked_responses: responses.RequestsMock,
):
    resource_key = "test_resource"
    base_url = DEFAULT_BASE_URL
    delete_call = mocked_responses.delete(
        f"{base_url}/resources/{resource_key}",
    )

    class TestApi(Api):
        @delete("/resources/{my_resource}")
        def delete_resource(self, my_resource: str):
            self.response.raise_for_status()

    api = TestApi(base_url=base_url)
    api.delete_resource(my_resource=resource_key)

    assert delete_call.call_count == 1


def test_delete_does_not_allow_body():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @delete("/resources/{my_resource}", body=Body())
            def delete_resource(self, my_resource: str, body: dict):
                self.response.raise_for_status()

    assert "Cannot pass Body() argument to @delete" in str(e)
