from pydantic import BaseModel
import pytest
import responses

from slink import Api, get, post, Query, Body

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
    base_url = DEFAULT_BASE_URL
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{base_url}/rest/api/3/{resource_key}/param",
        json=expected_response,
        match=[responses.matchers.query_param_matcher({"testvalue": testvalue})],
    )

    api = MyTestApi(base_url=DEFAULT_BASE_URL)
    result = api.get_resource_with_param(resource_key=resource_key, testvalue=testvalue)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_posts_json_body(mocked_responses: responses.RequestsMock):
    resource_key = "TEST"
    testvalue = "foo"
    base_url = DEFAULT_BASE_URL
    expected_response = {"name": "test_name", "value": 27}
    testbody = {"page": {"name": "first", "type": "json"}}
    post_method = mocked_responses.post(
        f"{base_url}/rest/api/3/{resource_key}",
        json=expected_response,
        match=[responses.matchers.json_params_matcher(testbody)],
    )

    api = MyTestApi(base_url=DEFAULT_BASE_URL)
    result = api.post_resource(resource_key=resource_key, body=testbody)

    assert post_method.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


# put
# del
# patch


def test_it_raises_error_if_position_args_used():
    api = MyTestApi(base_url=DEFAULT_BASE_URL)
    with pytest.raises(Exception) as excinfo:
        api.get_resource("resource_key")

    assert "Must use keyword arguments in api calls" in str(excinfo)


def test_it_raises_exception_if_decorator_has_references_not_in_signature():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get("rest/api/3/{some_other_arg}")
            def get_api(self, my_arg: str):
                return self.response.json()

        # TODO: it would be better to check it before the call with inspect
        TestApi(base_url=DEFAULT_BASE_URL).get_api(my_arg="foo")

    assert "Cannot match 'some_other_arg' in url to function parameters" in str(e)


def test_it_raises_exception_for_multiple_json_body(
    mocked_responses: responses.RequestsMock,
):
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @post("rest/api/3", body=Body(), body2=Body())
            def post_resource(self, resource_key: str, body: dict, body2: dict):
                pass

    assert "Can only have one Body() argument to @post" in str(e)


def test_it_raises_exception_for_get_with_body(
    mocked_responses: responses.RequestsMock,
):
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get("rest/api/3", body=Body())
            def post_resource(self, body: dict):
                pass

    assert "Cannot pass Body() argument to @get" in str(e)


def test_it_raises_exceptions_in_response_parsing(
    mocked_responses: responses.RequestsMock,
):
    base_url = DEFAULT_BASE_URL
    mocked_responses.get(
        f"{base_url}/rest/api/3",
        json={"message": "hello world"},
    )
    msg = "Failure to parse response"

    class ExceptionalApi(Api):
        @get("rest/api/3")
        def get_api(self, my_arg: str):
            raise Exception(msg)

    api = ExceptionalApi(base_url=base_url)

    with pytest.raises(Exception) as e:
        api.get_api(my_arg="foo")

    # not the best test, just making sure it passes up exceptions
    assert msg in str(e)


def test_it_raises_error_if_base_url_is_missing_scheme():
    with pytest.raises(Exception) as e:
        MyTestApi(base_url="hostname.without.scheme")
