from typing import Dict, List, Optional, Protocol, Generator, Tuple, Union
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

    def check_response(self):
        pass

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
    def __init__(self, alias: str = ""):
        self.alias = alias


class Body:
    pass


class DecoratorParser:
    def __init__(self, kwargs) -> None:
        self.queryParams = {
            k: v.alias if len(v.alias) else k
            for k, v in kwargs.items()
            if type(v) == Query
        }
        self.bodyParams = [k for k, v in kwargs.items() if type(v) == Body]

    def parse(self, args, kwargs) -> Tuple[Dict[str, str], List[str]]:
        if len(args):
            raise Exception("Must use keyword arguments in api calls")

        params = {
            self.queryParams[k]: v for k, v in kwargs.items() if k in self.queryParams
        }
        body = [v for k, v in kwargs.items() if k in self.bodyParams]

        return params, body


PagerGeneratorType = Generator[
    Union[Tuple[str, dict], Tuple[str, None]], requests.Response, None
]


class Pager(Protocol):
    def pages(self, url: str) -> PagerGeneratorType:  # type: ignore
        pass
