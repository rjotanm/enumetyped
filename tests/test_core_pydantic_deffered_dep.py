import time

import pydantic
from typing import Any
from enumetyped import Content
from enumetyped.pydantic import EnumetypedPydantic


class ExampleFeed(EnumetypedPydantic[Content]):
    DM: type["ExampleFeed[DeferModel]"]
    DE: type["ExampleFeed[DeferEnum[Any]]"]
    DRM: type["ExampleFeed[DeferRecModel]"]
    DRE: type["ExampleFeed[DeferRecEnum[Any]]"]


class DeferModel(pydantic.BaseModel):
    a: str


class DeferEnum(EnumetypedPydantic[Content]):
    Var: type["DeferEnum[str]"]


class DeferRecModel(pydantic.BaseModel):
    a: ExampleFeed[Any]


class DeferRecEnum(EnumetypedPydantic[Content]):
    Var: type["DeferRecEnum[ExampleFeed[Any]]"]


def test_serialization_dm() -> None:
    data = ExampleFeed.DM(DeferModel(a="test"))
    serialized = data.model_dump_json()  # {"DM":{"a":"test"}}
    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert data == deserialized


def test_serialization_de() -> None:
    data = ExampleFeed.DE(DeferEnum.Var("test"))
    serialized = data.model_dump_json()  # {"DE":{"Var":"test"}}
    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert data == deserialized


def test_serialization_drm() -> None:
    data = ExampleFeed.DRM(DeferRecModel(a=ExampleFeed.DM(DeferModel(a="test"))))
    serialized = data.model_dump_json()  # {"DRM":{"a":{"DM":{"a":"test"}}}}
    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert data == deserialized


def test_serialization_dre() -> None:
    data = ExampleFeed.DRE(DeferRecEnum.Var(ExampleFeed.DM(DeferModel(a="test"))))
    serialized = data.model_dump_json()  # {"DRE":{"Var":{"DM":{"a":"test"}}}}
    deserialized: ExampleFeed[Any] = ExampleFeed.model_validate_json(serialized)
    assert data == deserialized
