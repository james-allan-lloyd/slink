import pytest
import responses

from slink import Api, get

from support import DEFAULT_BASE_URL, MyTestApi


def test_it_raises_error_if_position_args_used():
    api = MyTestApi(base_url=DEFAULT_BASE_URL)
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
        TestApi(base_url=DEFAULT_BASE_URL).get_api(my_arg="foo")

    assert "Cannot match 'some_other_arg' in url to function parameters" in str(e)


def test_it_raises_exceptions_in_response_parsing(
    mocked_responses: responses.RequestsMock,
):
    base_url = DEFAULT_BASE_URL
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
    base_url_without_scheme = "hostname.without.scheme"
    with pytest.raises(Exception) as e:
        MyTestApi(base_url=base_url_without_scheme)

    assert f"base_url '{base_url_without_scheme}' is missing scheme" in str(e)
