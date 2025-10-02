import pydantic
import json
from typing import Any
from enumetyped import Content, Empty
from enumetyped.pydantic import EnumetypedPydantic


class AdItem(pydantic.BaseModel):
    ...


class RootContainer(pydantic.RootModel[Any]):
    root: list["ExampleFeed[Any]"]


class ExampleFeed(EnumetypedPydantic[Content]):
    # variant with simple type
    Post: type["ExampleFeed[str]"]
    # variant with other pydantic or enumetyped model
    Ad: type["ExampleFeed[AdItem]"]

    # variant without value must have Content=Empty
    ClientGenericContainer: type["ExampleFeed[Empty]"]

    # forward self reference allowed, but it`s no practical use
    SelfRef: type["ExampleFeed[ExampleFeed[Any]]"]

    # self reference within generics in root models
    SelfList: type["ExampleFeed[RootContainer]"]

    # self reference within inplace generics
    # (RootModel used implicitly)
    SelfListForce: type["ExampleFeed[list[ExampleFeed[Any]]]"]


def test_serialization_many_with_type_adapter() -> None:
    # use adapter for serialization\\deserialization in complex types
    feed_adapter = pydantic.TypeAdapter(list[ExampleFeed[Any]])

    feed: list[ExampleFeed[Any]] = [
        ExampleFeed.Post("test"),
        ExampleFeed.Ad(AdItem()),
        ExampleFeed.ClientGenericContainer(),
    ]
    serialized = feed_adapter.dump_json(feed)  # [{"Post":"test"},{"Ad":{}},"ClientGenericContainer"]
    deserialized = feed_adapter.validate_json(serialized)
    assert feed == deserialized


# use in pydantic models as-is
class TopLevelModel(pydantic.BaseModel):
    feed: ExampleFeed[Any]


def test_serialization_inside_pydantic_model() -> None:
    data = TopLevelModel(feed=ExampleFeed.Post("test"))
    serialized = data.model_dump_json()  # {"feed":{"Post":"test"}}
    deserialized = TopLevelModel.model_validate_json(serialized)
    assert data == deserialized


def test_serialization_with_pydantic_like_methods() -> None:
    # use pydantic-like methods
    ad = ExampleFeed.Ad(AdItem())
    serialized = ad.model_dump_json()  # {"Ad":{}}
    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert ad == deserialized


def test_standard_constructor_empty_variant() -> None:
    # or use tagging-dependent constructor
    container = ExampleFeed.ClientGenericContainer()
    serialized = container.model_dump_json()  # "ClientGenericContainer" - External

    raw_deserialized = json.loads(serialized)
    deserialized = ExampleFeed(raw_deserialized)

    assert container == deserialized


def test_standard_constructor() -> None:
    post = ExampleFeed.Post("test")
    serialized = post.model_dump_json()  # {"Post":"test"}

    raw_deserialized = json.loads(serialized)
    deserialized = ExampleFeed(raw_deserialized)
    deserialized_kwargs: ExampleFeed[Any] = ExampleFeed(**raw_deserialized)

    assert post == deserialized
    assert post == deserialized_kwargs


def test_self_containing() -> None:
    # self containing
    self_containing = ExampleFeed.SelfRef(ExampleFeed.SelfRef(ExampleFeed.Post("test")))

    serialized = self_containing.model_dump_json()  # {"SelfRef":{"SelfRef":{"Post":"test"}}}

    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert self_containing == deserialized

    raw_deserialized = json.loads(serialized)
    deserialized = ExampleFeed(raw_deserialized)
    deserialized_kwargs: ExampleFeed[Any] = ExampleFeed(**raw_deserialized)

    assert self_containing == deserialized
    assert self_containing == deserialized_kwargs


def test_self_containing_with_container() -> None:
    # self containing with generic container
    self_containing = ExampleFeed.SelfList(RootContainer(root=[ExampleFeed.SelfRef(ExampleFeed.Post("test"))]))

    serialized = self_containing.model_dump_json()  # {"SelfList":[{"SelfRef":{"Post":"test"}}]}

    raw_deserialized = json.loads(serialized)
    deserialized = ExampleFeed(raw_deserialized)
    deserialized_kwargs: ExampleFeed[Any] = ExampleFeed(**raw_deserialized)
    deserialized_forward: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)

    assert self_containing == deserialized
    assert self_containing == deserialized_kwargs
    assert self_containing == deserialized_forward


def test_self_containing_with_container_via_implicitly_root_model() -> None:
    # self containing with generic container (implicitly create RootModel)
    self_containing = ExampleFeed.SelfListForce([ExampleFeed.SelfRef(ExampleFeed.Post("test"))])

    serialized = self_containing.model_dump_json()  # {"SelfListForce":[{"SelfRef":{"Post":"test"}}]}

    raw_deserialized = json.loads(serialized)
    deserialized = ExampleFeed(raw_deserialized)
    deserialized_kwargs: ExampleFeed[Any] = ExampleFeed(**raw_deserialized)
    deserialized_forward: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)

    assert self_containing == deserialized
    assert self_containing == deserialized_kwargs
    assert self_containing == deserialized_forward
