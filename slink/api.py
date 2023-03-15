import functools
from typing import Any, Optional, Protocol, Generator, Tuple
from urllib.parse import urljoin, urlparse
import requests
import inspect


class Api:
    def __init__(self, base_url="", session: Optional[requests.Session] = None) -> None:
        parsed_url = urlparse(base_url)
        if parsed_url.scheme == "":
            raise Exception(f"base_url '{base_url}' is missing scheme")
        self.session = session if session else requests.Session()
        self.base_url = base_url
        self._response: Optional[requests.Response] = None

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

    def parse(self, args, kwargs) -> Tuple[dict[str, str], list[str]]:
        if len(args):
            raise Exception("Must use keyword arguments in api calls")

        params = {k: v for k, v in kwargs.items() if k in self.queryParams}
        body = [v for k, v in kwargs.items() if k in self.bodyParams]

        return params, body


class Pager(Protocol):
    def pages(self, url: str) -> Generator[Tuple[str, dict], None, None]:  # type: ignore
        pass

    def process(self, response: requests.Response):
        pass


def _wrap_response_func(
    method: str, url_template: str, decoratorParser: DecoratorParser
):
    def wrap(process_response):
        @functools.wraps(process_response)
        def make_request(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(args, kwargs)
            json = body[0] if len(body) else None
            url = self.construct_url(url_template, kwargs)
            self._response = self.session.request(
                method=method, url=url, params=params, json=json
            )
            result = process_response(self, **kwargs)
            self._response = None
            return result

        return make_request

    return wrap


def get(url_template, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 0:
        raise Exception(
            f"Cannot pass Body() argument to @get (got {', '.join(decoratorParser.bodyParams)})"
        )

    return _wrap_response_func(
        "GET", url_template=url_template, decoratorParser=decoratorParser
    )


def post(url_template: str, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 1:
        raise Exception(
            f"Can only have one Body() argument to @post (got {', '.join(decoratorParser.bodyParams)})"
        )

    return _wrap_response_func(
        "POST", url_template=url_template, decoratorParser=decoratorParser
    )


def get_pages(url_template, pager: Optional[Pager] = None, **kwargs):
    if pager is None:
        raise ValueError("Must supply pager argument to get_pages")

    pager_actual = pager  # allow type deduction in inner function

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
            for url, params in pager_actual.pages(url):
                params.update(params)
                self._response = self.session.get(url, params=params)
                pager_actual.process(self._response)
                for value in get_impl(self, *args, **kwargs):
                    yield value
                self._response = None

        return call_get

    return wrap_get
