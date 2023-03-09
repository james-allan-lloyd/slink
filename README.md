# Slink
Inspired by uplink, a simple way to build rest API clients without OpenAPI.

# Install
poetry install

# Basic Usage
Model your resource in Pydantic
```python
class MyResource(BaseModel):
    name: str
    value: int
```

Create an API
```python
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