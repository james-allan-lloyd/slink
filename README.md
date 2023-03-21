# Slink

Inspired by [uplink](https://uplink.readthedocs.io/en/stable/), a simple way to build rest API clients without OpenAPI,
and without a lot of requests boilerplate.

## Install

```shell
poetry install
```

## Basic Usage

Model your resource in Pydantic

```python
from pydantic import BaseModel
class MyResource(BaseModel):
    name: str
    value: int
```

Create an API

```python
from slink import Api, get, post, Query, Body

class MyTestApi(Api):

    # Define a get
    @get("rest/api/3/{resource_key}")
    def get_resource(self, resource_key: str):
        return MyResource(**self.response.json())

    # Define it with some query params
    @get("rest/api/3/{resource_key}/param", testvalue=Query())
    def get_resource_with_param(self, resource_key: str, testvalue: str):
        return MyResource(**self.response.json())

    # And post your body content
    @post("rest/api/3/{resource_key}", body=Body())
    def post_resource(self, resource_key: str, body: dict):
        return MyResource(**self.response.json())
```

Then use it:

```python
api = MyTestApi(base_url="http://example.com/")
result = api.get_resource(resource_key="REST")
result = api.get_resource_with_param(resource_key="REST", testvalue="test")
result = api.post_resource(resource_key="TEST", body={"foo": "bar"})
```

## Pagination

Slink allows you to elegantly iterate most style of paged APIs. As example, we can implement one of the most common
pagination patterns, an an offseted pagination API. With such an API, you request an offset of the dataset with some
limit on the size of the data returned:

```python
class OffsettedPager:
    def __init__(self, max_count=5) -> None:
        self.max_count = max_count

    def pages(self, url: str) -> Generator[Tuple[str, dict], requests.Response, None]:
        start_at = 0
        total = None
        while total is None or start_at < total:
            # yield a tuple of the next url and any parameters to be added to the original request, get back the response to update the iteration
            response = yield url, {
                "startAt": start_at,
                "maxCount": self.max_count,
            }
            total = response.json()["total"]
            start_at += self.max_count
```

You can then use the pager with the `@get_pages` decorator to iterate through the pages:

```python
class PagedApi(Api):
    @get_pages("rest/api/3/pages", pager=OffsetedPager())
    def get_paginated(self)
        # our data field in the json result just contains a list of ints, but they could be a much more complicated object
        for value in self.response.json()["data"]:
            yield int(value)

api = PagedApi(base_url=base_url)
all_results = list(api.get_paginated())  # note the list construction because pages are returned as generators
```

Another example would be a pagination API where there is a next link:

```python
class LinkedPager:
    def pages(self, url) -> Generator[Tuple[str, dict], requests.Response, None]:
        response = yield url, {}  # first page is just the raw url
        # use assignment operator since python 3.8
        while next_url := response.json()["links"].get("next"):
            response = yield next_url, {}
```

Note in both cases, iteration can be stopped early by simply stopping calling the endpoint, ie the following will make
any more requests once it finds the required value:

```python
for e in api.get_paginated():
    if e == value_to_find:
        break
```

## Limitations and TODOs

- [x] ~~put, delete~~
- [ ] error handling and robustness
- [ ] retry patterns
- [ ] patch, head
- [ ] supporting other http client libraries, including async ones
