from typing import Generator
import pytest
import responses

from slink import Api, get_pages
from slink.api import Query

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
    actual_results = []
    for elem in api.get_paginated():
        actual_results.append(elem)

    assert actual_results == data


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
