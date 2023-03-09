from urllib.parse import urljoin
import requests
import inspect


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
