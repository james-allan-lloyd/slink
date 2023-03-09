import inspect
from urllib.parse import urljoin
from pydantic import BaseModel
import requests
import responses as resp


class Api:
    def __init__(self, base_url="", session: requests.Session | None = None) -> None:
        self.session = session if session else requests.Session()
        self.base_url = base_url
        self._response: requests.Response | None

    @property
    def response(self) -> requests.Response:
        if self._response is not None:
            return self._response
        else:
            raise Exception("No current response!")

    def check_signature(self, signature: inspect.Signature, args, kwargs):
        signature.bind(self, *args, **kwargs)

    def construct_url(self, url_template, kwargs):
        return urljoin(
            self.base_url,
            url_template.format(**kwargs),
        )


class Query:
    def __init__(self) -> None:
        pass


class Body:
    def __init__(self) -> None:
        pass


class DecoratorParser:
    def __init__(self, kwargs, func) -> None:
        self.queryParams = [k for k, v in kwargs.items() if type(v) == Query]
        self.bodyParams = [k for k, v in kwargs.items() if type(v) == Body]
        self.func = func
        self.signature = inspect.signature(func)

    def parse(self, api, args, kwargs):
        self.signature.bind(api, *args, **kwargs)
        params = {k: v for k, v in kwargs.items() if k in self.queryParams}
        body = [v for k, v in kwargs.items() if k in self.bodyParams]

        return params, body


def get(url_template, **kwargs):
    def wrap_get(get_impl):
        decoratorParser = DecoratorParser(kwargs, get_impl)

        def call_get(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(self, args, kwargs)
            url = self.construct_url(url_template, kwargs)

            self._response = self.session.get(url, params=params)
            result = get_impl(self, *args, **kwargs)
            self._response = None
            return result

        return call_get

    return wrap_get


def post(url_template: str, **kwargs):
    def wrap_post(post_impl):
        decoratorParser = DecoratorParser(kwargs, post_impl)

        def call_post(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(self, args, kwargs)
            url = self.construct_url(url_template, kwargs)

            self._response = self.session.post(url, params=params, json=body[0])
            result = post_impl(self, *args, **kwargs)
            self._response = None
            return result

        return call_post

    return wrap_post


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
