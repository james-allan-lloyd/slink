from pydantic import BaseModel
import pytest
import responses
from slink.api import Api, Body
from slink.decorators import get
from support import DEFAULT_BASE_URL, MyTestApi


def test_it_gets(mocked_responses: responses.RequestsMock):
    resource_key = "TEST"
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{DEFAULT_BASE_URL}/rest/api/3/{resource_key}",
        json=expected_response,
    )

    class TestApi(Api):
        class Resource(BaseModel):
            name: str
            value: int

        @get("rest/api/3/{resource_key}")
        def get_resource(self, resource_key: str):
            return TestApi.Resource(**self.response.json())

    api = TestApi(base_url=DEFAULT_BASE_URL)
    result = api.get_resource(resource_key=resource_key)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_gets_with_params(mocked_responses: responses.RequestsMock):
    resource_key = "TEST"
    testvalue = "foo"
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{DEFAULT_BASE_URL}/rest/api/3/{resource_key}/param",
        json=expected_response,
        match=[responses.matchers.query_param_matcher({"testvalue": testvalue})],
    )

    api = MyTestApi(base_url=DEFAULT_BASE_URL)
    result = api.get_resource_with_param(resource_key=resource_key, testvalue=testvalue)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_raises_exception_for_get_with_body():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get("rest/api/3", body=Body())
            def post_resource(self, body: dict):
                pass

    assert "Cannot pass Body() argument to @get" in str(e)
