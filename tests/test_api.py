from dataclasses import dataclass
from typing import Any, Generator, Iterator
from urllib.parse import urljoin
from pydantic import BaseModel
import pytest
import responses as resp

from slink import Api, get, post, Query, Body, get_pages
from slink.api import Page


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

    @get("rest/api/3/pages")
    def get_paginated(self):
        return MyResource(**self.response.json())


@pytest.fixture
def mocked_responses():
    with resp.RequestsMock() as rsps:
        yield rsps


def test_it_gets(mocked_responses):
    resource_key = "TEST"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{base_url}/rest/api/3/{resource_key}",
        json=expected_response,
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.get_resource(resource_key=resource_key)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_gets_with_params(mocked_responses):
    resource_key = "TEST"
    testvalue = "foo"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    get_project = mocked_responses.get(
        f"{base_url}/rest/api/3/{resource_key}/param",
        json=expected_response,
        match=[resp.matchers.query_param_matcher({"testvalue": testvalue})],
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.get_resource_with_param(resource_key=resource_key, testvalue=testvalue)

    assert get_project.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


def test_it_posts_json_body(mocked_responses):
    resource_key = "TEST"
    testvalue = "foo"
    base_url = "http://example.com"
    expected_response = {"name": "test_name", "value": 27}
    testbody = {"page": {"name": "first", "type": "json"}}
    post_method = mocked_responses.post(
        f"{base_url}/rest/api/3/{resource_key}",
        json=expected_response,
        match=[resp.matchers.json_params_matcher(testbody)],
    )

    api = MyTestApi(base_url="http://example.com/")
    result = api.post_resource(resource_key=resource_key, body=testbody)

    assert post_method.call_count == 1
    assert result.name == expected_response["name"]
    assert result.value == expected_response["value"]


class SimplePager:
    def __init__(self, maxCount=5) -> None:
        self.maxCount = maxCount
        self.startAt = 0
        self.total = None

    def pages(self, url):
        while self.total is None or self.startAt < self.total:
            yield url, {"startAt": self.startAt, "maxCount": self.maxCount}
            self.startAt += self.maxCount

    def process(self, response):
        self.total = response.json()["total"]


def setup_page_responses(
    mocked_responses: resp.RequestsMock, base_url, data, page_limit=None
):
    page_responses: list[resp.BaseResponse] = []
    for i in range(0, 20, 5):
        if page_limit and i >= page_limit * 5:
            break
        page = {
            "data": data[i : i + 5],
            "total": len(data),
            "maxResults": 5,
        }
        print(page)
        page_responses.append(
            mocked_responses.get(
                f"{base_url}/rest/api/3/pages",
                json=page,
                match=[
                    resp.matchers.query_param_matcher({"startAt": i, "maxCount": 5})
                ],
            )
        )
    return page_responses


def test_it_supports_pagination_directly(mocked_responses):
    base_url = "http://example.com"
    data = list(range(1, 20))
    setup_page_responses(mocked_responses, base_url, data)

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=SimplePager())
        def get_paginated(self):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)
    actual_results = []
    for elem in api.get_paginated():
        actual_results.append(elem)

    assert actual_results == data


def test_it_supports_early_termination(mocked_responses):
    """
    its important that we allow pagination to terminate early, so we don't force the user to iterate all pages all the
    time
    """
    base_url = "http://example.com"
    data = list(range(1, 20))
    page_responses = setup_page_responses(
        mocked_responses, base_url, data, page_limit=2
    )

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=SimplePager())
        def get_paginated(self) -> Generator[int, None, None]:
            for value in self.response.json()["data"]:
                yield value

    api = PagedApi(base_url=base_url)
    for elem in api.get_paginated():
        if elem == 6:
            break

    assert page_responses[0].call_count == 1
    assert page_responses[1].call_count == 1


class LinkedPager:
    def __init__(self) -> None:
        self.next_url = None

    def pages(self, url):
        yield url, {}  # first page is just the raw url
        while self.next_url:
            yield self.next_url, {}

    def process(self, response):
        self.next_url = response.json()["links"].get("next")


def test_it_supports_linked_page_iterators(mocked_responses):
    """
    Another style of iterators is the linked page iterator, where the link to the next page is contained in the
    response.
    """
    base_url = "http://example.com"
    data = list(range(1, 20))
    num_pages = 4
    for i in range(0, num_pages):
        page = {
            "data": data[i * 5 : (i + 1) * 5],
            "total": len(data),
            "links": {"next": f"{base_url}/rest/api/3/pages?page={i+1}"},
        }
        if i + 1 >= num_pages:
            page["links"] = {}
        print(page)
        if i == 0:
            mocked_responses.get(
                f"{base_url}/rest/api/3/pages",
                json=page,
            )
        else:
            mocked_responses.get(
                f"{base_url}/rest/api/3/pages",
                json=page,
                match=[
                    resp.matchers.query_param_matcher(
                        {
                            "page": i,
                        }
                    )
                ],
            )

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=LinkedPager())
        def get_paginated(self):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)
    actual_data = [e for e in api.get_paginated()]

    assert actual_data == data


# put
# del
# patch


def test_it_raises_error_if_position_args_used():
    api = MyTestApi(base_url="http://example.com")
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
        TestApi(base_url="http://example.com").get_api(my_arg="foo")

    assert "Cannot match 'some_other_arg' in url to function parameters" in str(e)


def test_it_raises_exception_for_multiple_json_body(mocked_responses):
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @post("rest/api/3", body=Body(), body2=Body())
            def post_resource(self, resource_key: str, body: dict, body2: dict):
                pass

    assert "Can only have one Body() argument to @post" in str(e)


def test_it_raises_exception_for_get_with_body(mocked_responses):
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get("rest/api/3", body=Body())
            def post_resource(self, body: dict):
                pass

    assert "Cannot pass Body() argument to @get" in str(e)


def test_it_raises_exceptions_in_response_parsing(mocked_responses):
    base_url = "http://example.com"
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


def test_it_throws_if_get_pages_is_given_no_pager():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get_pages("rest/api/3")
            def get_api(self, my_arg: str):
                pass

    assert "Must supply pager argument to get_pages" in str(e)
