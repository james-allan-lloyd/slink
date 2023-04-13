import copy
import functools
import logging
from typing import Optional
from .api import Api, DecoratorParser, Pager

logger = logging.getLogger("slink")


def _wrap_response_func(
    method: str, url_template: str, decoratorParser: DecoratorParser
):
    def wrap(process_response):
        @functools.wraps(process_response)
        def make_request(self: Api, *args, **kwargs):
            params, body = decoratorParser.parse(args, kwargs)
            json = body[0] if len(body) else None
            url = self.construct_url(url_template, kwargs)
            logger.debug(
                f"{method} {url} params={params} body={'yes' if json else 'no'}"
            )
            self._response = self.session.request(
                method=method, url=url, params=params, json=json
            )
            self.check_response()
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


def delete(url_template: str, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 0:
        raise Exception(
            f"Cannot pass Body() argument to @delete (got {', '.join(decoratorParser.bodyParams)})"
        )

    return _wrap_response_func(
        "DELETE", url_template=url_template, decoratorParser=decoratorParser
    )


def put(url_template: str, **kwargs):
    decoratorParser = DecoratorParser(kwargs)
    if len(decoratorParser.bodyParams) > 1:
        raise Exception(
            f"Can only have one Body() argument to @put (got {', '.join(decoratorParser.bodyParams)})"
        )

    return _wrap_response_func(
        "PUT", url_template=url_template, decoratorParser=decoratorParser
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
            page_generator = pager_actual.pages(url)
            response = None
            try:
                while True:
                    url, page_params = (
                        page_generator.send(response)
                        if response
                        else next(page_generator)
                    )
                    params.update(page_params)
                    response = self.session.get(url, params=params)
                    assert response
                    self._response = response
                    self.check_response()
                    for value in get_impl(self, *args, **kwargs):
                        yield value
            except StopIteration:
                pass
            finally:
                self._response = None

        return call_get

    return wrap_get
