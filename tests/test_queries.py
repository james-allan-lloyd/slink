from pydantic import BaseModel
import pytest
import responses
from slink.api import Api, Body, Query
from slink.decorators import get
from support import DEFAULT_BASE_URL, MyTestApi


def test_aliased_queries(mocked_responses: responses.RequestsMock):
    resource_key = "TEST"
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{DEFAULT_BASE_URL}/rest/api/3/{resource_key}",
        json=expected_response,
        match=[responses.matchers.query_param_matcher({"$param": "foo"})],
    )

    class TestApi(Api):
        class Resource(BaseModel):
            name: str
            value: int

        @get("rest/api/3/{resource_key}", param=Query("$param"))
        def get_resource(self, resource_key: str, param: str):
            return TestApi.Resource(**self.response.json())

    api = TestApi(base_url=DEFAULT_BASE_URL)
    result = api.get_resource(resource_key=resource_key, param="foo")

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]
