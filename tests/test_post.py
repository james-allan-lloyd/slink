import pytest
import responses
from slink import Api, Body, post

from support import DEFAULT_BASE_URL, MyTestApi


def test_it_posts_json_body(mocked_responses: responses.RequestsMock):
    resource_key = "TEST"
    testvalue = "foo"
    expected_response = {"name": "test_name", "value": 27}
    testbody = {"page": {"name": "first", "type": "json"}}
    post_method = mocked_responses.post(
        f"{DEFAULT_BASE_URL}/rest/api/3/{resource_key}",
        json=expected_response,
        match=[responses.matchers.json_params_matcher(testbody)],
    )

    api = MyTestApi(base_url=DEFAULT_BASE_URL)
    result = api.post_resource(resource_key=resource_key, body=testbody)

    assert post_method.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_raises_exception_for_multiple_json_body():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @post("rest/api/3", body=Body(), body2=Body())
            def post_resource(self, resource_key: str, body: dict, body2: dict):
                pass

    assert "Can only have one Body() argument to @post" in str(e)
