from pydantic import BaseModel
import responses

from slink import Api, get, post, Query, Body

DEFAULT_BASE_URL = "http://example.com"


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


def setup_page_responses(
    mocked_responses: responses.RequestsMock, base_url, data, page_limit=None
):
    page_responses: list[responses.BaseResponse] = []
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
                    responses.matchers.query_param_matcher(
                        {"startAt": i, "maxCount": 5}
                    )
                ],
            )
        )
    return page_responses


class SimplePager:
    def __init__(self, maxCount=5) -> None:
        self.maxCount = maxCount

    def pages(self, url):
        startAt = 0
        total = None
        while total is None or startAt < total:
            response = yield url, {"startAt": startAt, "maxCount": self.maxCount}
            if response:
                print("iterator response", response)
                total = response.json()["total"]
                startAt += self.maxCount


class LinkedPager:
    def __init__(self) -> None:
        # self.next_url = None
        pass

    def pages(self, url):
        response = yield url, {}  # first page is just the raw url
        next_url = response.json()["links"].get("next")
        while next_url:
            response = yield next_url, {}
            if response:
                next_url = response.json()["links"].get("next")

    # def process(self, response):
    #     self.next_url = response.json()["links"].get("next")
