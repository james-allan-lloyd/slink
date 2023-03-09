from pydantic import BaseModel
import responses as resp

from slink import Api, get, post, Query, Body


class MyResource(BaseModel):
    name: str
    value: int


class MyTestApi(Api):
    @get("rest/api/3/{resource_key}")
    def get_resource(self, resource_key: str):
        return MyResource(**self.response.json())

    @get("rest/api/3/{resource_key}/param", testvalue=Query())
    def get_resource_with_param(self, resource_key: str, testvalue: str):
        return MyResource(**self.response.json())

    @post("rest/api/3/{resource_key}", body=Body())
    def post_resource(self, resource_key: str, body: dict):
        return MyResource(**self.response.json())


@resp.activate
def test_it_gets():
    resource_key = "TEST"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    get_project = resp.get(
        f"{base_url}/rest/api/3/{resource_key}",
        json=expected_response,
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.get_resource(resource_key=resource_key)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


@resp.activate
def test_it_gets_with_params():
    resource_key = "TEST"
    testvalue = "foo"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    get_project = resp.get(
        f"{base_url}/rest/api/3/{resource_key}/param",
        json=expected_response,
        match=[resp.matchers.query_param_matcher({"testvalue": testvalue})],
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.get_resource_with_param(resource_key=resource_key, testvalue=testvalue)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


@resp.activate
def test_it_posts_json_body():
    resource_key = "TEST"
    testvalue = "foo"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    testbody = {"page": {"name": "first", "type": "json"}}
    post_method = resp.post(
        f"{base_url}/rest/api/3/{resource_key}",
        json=expected_response,
        match=[resp.matchers.json_params_matcher(testbody)],
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.post_resource(resource_key=resource_key, body=testbody)

    assert post_method.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_supports_pagination_directly():
    pass


# put
# del
# patch


def test_it_raises_exception_if_decorator_has_references_not_in_signature():
    pass


def test_it_raises_exception_for_multiple_json_body():
    pass


def test_it_raises_exception_for_get_with_body():
    pass
