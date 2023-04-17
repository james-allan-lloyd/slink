from ast import Tuple
from typing import Generator
import pytest
import requests
import responses

from slink import Api, get_pages
from slink.api import PagerGeneratorType, Query

from support import DEFAULT_BASE_URL, setup_page_responses, SimplePager, LinkedPager


def test_it_supports_pagination_directly(mocked_responses):
    base_url = DEFAULT_BASE_URL
    data = list(range(1, 20))
    setup_page_responses(mocked_responses, base_url, data)

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=SimplePager())
        def get_paginated(self):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)
    actual_results = list(api.get_paginated())

    assert actual_results == data


def test_it_supports_multiple_calls(mocked_responses):
    base_url = DEFAULT_BASE_URL
    data = list(range(1, 20))
    setup_page_responses(mocked_responses, base_url, data)

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=SimplePager())
        def get_paginated(self):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)

    first_results = list(api.get_paginated())
    second_results = list(api.get_paginated())

    assert first_results == second_results


def test_it_supports_pagination_with_params(mocked_responses):
    base_url = DEFAULT_BASE_URL
    data = list(range(1, 20))
    page_responses: list[responses.BaseResponse] = []
    for i in range(0, 20, 5):
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
                    responses.matchers.query_param_matcher(
                        {"startAt": i, "maxCount": 5, "foo": "bar"}
                    )
                ],
            )
        )

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=SimplePager(), foo=Query())
        def get_paginated(self, foo: str):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)
    actual_results = []
    for elem in api.get_paginated(foo="bar"):
        actual_results.append(elem)

    assert actual_results == data


def test_it_overrides_pagination_params(mocked_responses):
    """
    Different to the former case, include a parameter that needs to be overriden BY a pagination parameter.

    FIXME: right now, this means that the startAt parameter is kind of useless - it'll always be overriden. Would be
    nice to support the use case of beginning at a specific page (resuming pagingation, say).
    """
    base_url = DEFAULT_BASE_URL
    data = list(range(1, 20))
    page_responses: list[responses.BaseResponse] = []
    for i in range(0, 20, 5):
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
                    responses.matchers.query_param_matcher(
                        {"startAt": i, "maxCount": 5, "foo": "bar"}
                    )
                ],
            )
        )

    class PagedApi(Api):
        @get_pages(
            "rest/api/3/pages", pager=SimplePager(), foo=Query(), startAt=Query()
        )
        def get_paginated(self, foo: str, startAt: int):
            for value in self.response.json()["data"]:
                yield int(value)

    api = PagedApi(base_url=base_url)
    actual_results = []
    for elem in api.get_paginated(foo="bar", startAt=5):
        actual_results.append(elem)

    assert actual_results == data


def test_it_supports_early_termination(mocked_responses):
    """
    its important that we allow pagination to terminate early, so we don't force the user to iterate all pages all the
    time
    """
    base_url = DEFAULT_BASE_URL
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


def test_it_supports_linked_page_iterators(mocked_responses):
    """
    Another style of iterators is the linked page iterator, where the link to the next page is contained in the
    response.
    """
    base_url = DEFAULT_BASE_URL
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
                    responses.matchers.query_param_matcher(
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


def test_it_throws_if_get_pages_is_given_no_pager():
    with pytest.raises(Exception) as e:

        class TestApi(Api):
            @get_pages("rest/api/3")
            def get_api(self, my_arg: str):
                pass

    assert "Must supply pager argument to get_pages" in str(e)


@pytest.fixture
def generated_cursor_data(mocked_responses):
    base_url = DEFAULT_BASE_URL
    data = list(range(1, 20))
    num_pages = 4
    for i in range(0, num_pages):
        page = {
            "data": data[i * 5 : (i + 1) * 5],
            "total": len(data),
            "links": {"next": f"{base_url}/rest/api/3/pages?cursor={i+1}"},
        }
        if i + 1 >= num_pages:
            page["links"] = {}
        if i == 0:
            mocked_responses.get(
                f"{base_url}/rest/api/3/pages",
                json=page,
                match=[
                    responses.matchers.query_param_matcher(
                        {
                            "my_arg": "foo",
                        }
                    )
                ],
            )
        else:
            mocked_responses.get(
                f"{base_url}/rest/api/3/pages",
                json=page,
                match=[
                    responses.matchers.query_param_matcher(
                        {
                            "cursor": i,
                        }
                    )
                ],
            )

    return data


def test_pagers_can_return_none_to_allow_page_url_as_is(generated_cursor_data):
    """
    For pagination schemes where there is just a "next page" link, we want to avoid adding paramters from the original call (as parsed by the decorator). To do this, you can just return None from the page generator.
    """

    class CursorPager:
        def pages(self, url: str) -> PagerGeneratorType:
            response = yield url, {}  # first page is just the raw url
            while next_url := response.json()["links"].get("next"):
                response = yield next_url, None

    class PagedApi(Api):
        @get_pages("rest/api/3/pages", pager=CursorPager(), my_arg=Query())
        def get_paginated(self, my_arg: str):
            for x in self.response.json()["data"]:
                yield x

    api = PagedApi(base_url=DEFAULT_BASE_URL)
    actual_data = list(api.get_paginated(my_arg="foo"))

    assert actual_data == generated_cursor_data
