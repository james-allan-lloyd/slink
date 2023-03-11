import functools
from typing import Any, Protocol, Generator, Tuple
from urllib.parse import urljoin, urlparse
from attr import dataclass
import requests
import inspect


class Api:
    def __init__(self, base_url="", session: requests.Session | None = None) -> None:
        parsed_url = urlparse(base_url)
        if parsed_url.scheme == "":
            raise Exception(f"base_url '{base_url}' is missing scheme")
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

    def construct_url(self, url_template: str, kwargs: dict):
        try:
            formatted_url = url_template.format_map(kwargs)
        except KeyError as e:
            raise Exception(f"Cannot match '{e.args[0]}' in url to function parameters")
        return urljoin(
            self.base_url,
            formatted_url,
        )


class Query:
    pass


class Body:
    pass


class DecoratorParser:
    def __init__(self, kwargs) -> None:
        self.queryParams = [k for k, v in kwargs.items() if type(v) == Query]
        self.bodyParams = [k for k, v in kwargs.items() if type(v) == Body]

    def parse(self, args, kwargs):
        if len(args):
            raise Exception("Must use keyword arguments in api calls")

        params = {k: v for k, v in kwargs.items() if k in self.queryParams}
        body = [v for k, v in kwargs.items() if k in self.bodyParams]

        return params, body


def get(url_template, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 0:
        raise Exception(
            f"Cannot pass Body() argument to @get (got {', '.join(decoratorParser.bodyParams)})"
        )

    def wrap_get(get_impl):
        @functools.wraps(get_impl)
        def call_get(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(args, kwargs)
            url = self.construct_url(url_template, kwargs)
            self._response = self.session.get(url, params=params)
            result = get_impl(self, **kwargs)
            self._response = None
            return result

        return call_get

    return wrap_get


@dataclass
class Page:
    params: dict[str, Any]
    url: str


class Pager(Protocol):
    def pages(self, url: str) -> Generator[Tuple[str, dict], None, None]:  # type: ignore
        pass

    def process(self, response: requests.Response):
        pass


def get_pages(url_template, pager: Pager | None = None, **kwargs):
    if pager is None:
        raise ValueError("Must supply pager argument to get_pages")

    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 0:
        raise Exception(
            f"Cannot pass Body() argument to @get_pages (got {', '.join(decoratorParser.bodyParams)})"
        )

    def wrap_get(get_impl):
        @functools.wraps(get_impl)
        def call_get(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(args, kwargs)
            url = self.construct_url(url_template, kwargs)
            for url, params in pager.pages(url):
                params.update(params)
                self._response = self.session.get(url, params=params)
                pager.process(self._response)
                for value in get_impl(self, *args, **kwargs):
                    yield value
                self._response = None

        return call_get

    return wrap_get


def post(url_template: str, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 1:
        raise Exception(
            f"Can only have one Body() argument to @post (got {', '.join(decoratorParser.bodyParams)})"
        )

    def wrap_post(post_impl):
        @functools.wraps(post_impl)
        def call_post(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(args, kwargs)
            url = self.construct_url(url_template, kwargs)

            self._response = self.session.post(url, params=params, json=body[0])
            result = post_impl(self, *args, **kwargs)
            self._response = None
            return result

        return call_post

    return wrap_post
