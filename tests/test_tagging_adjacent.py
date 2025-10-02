import json
from dataclasses import dataclass
from typing import Any, Optional

import pydantic
from pydantic import BaseModel
from typing_extensions import Annotated, TypedDict

from enumetyped import Content
from enumetyped import Empty
from enumetyped.pydantic import FieldMetadata, EnumetypedPydantic, Rename
from enumetyped.pydantic.serialization.external import AlwaysSerializeToDict


@dataclass
class TDataClass1:
    a: int


class TModel1(BaseModel):
    b: str


class TD1(TypedDict):
    b: str


class SimpleEnum1(EnumetypedPydantic[Empty]):
    V1: type["SimpleEnum1"]
    V2: type["SimpleEnum1"]


class OtherEnum1(EnumetypedPydantic[Content]):
    D: type["OtherEnum1[TD1]"]
    C: type["OtherEnum1[TDataClass1]"]
    Int: type["OtherEnum1[int]"]


class MyEnumAdjacent(EnumetypedPydantic[Content], variant="tag", content="payload"):
    # MyEnum.Int(123)
    Int: type["MyEnumAdjacent[int]"]

    # MyEnum.Str(123)
    Str: type["MyEnumAdjacent[str]"]

    # MyEnum.Str(OtherEnum.Int(1))
    Other: type["MyEnumAdjacent[OtherEnum1[Any]]"]  # any from OtherEnum variants

    # MyEnum.Str(MyEnum.Int(1)) | MyEnum.Str(MyEnum.Str(1))
    Self: type["MyEnumAdjacent[MyEnumAdjacent[Any]]"]  # any from self variants

    # MyEnum.OnlySelf(...) - any parameters skipped
    NoValue: type["MyEnumAdjacent[Empty]"]

    # MyEnum.OnlySelf2(None)
    Optional: type["MyEnumAdjacent[Optional[bool]]"]

    # MyEnum.List(["1", "2", "3"])
    List: type["MyEnumAdjacent[list[str]]"]

    # MyEnum.Dict({"key": "value"})
    Dict: type["MyEnumAdjacent[dict[str, str]]"]
    # TypedDict: type["MyEnum[{"b": str}]"]
    TypedDict: type["MyEnumAdjacent[TD1]"]  # python does not have inline TypedDict now

    # MyEnum.DC(TestDataClass(a=1))
    DataClass: type["MyEnumAdjacent[TDataClass1]"]

    # MyEnum.Model(TestModel(b="2"))
    Model: type["MyEnumAdjacent[TModel1]"]

    # MyEnum.StrTuple(("1", "2")))
    StringTuple: Annotated[type["MyEnumAdjacent[tuple[str, str]]"], FieldMetadata(rename="just_str_tuple")]

    # or use typenum.pydantic.Rename
    StrTuple: Annotated[type["MyEnumAdjacent[tuple[str, str]]"], Rename("some_other_name")]


def test_isinstance() -> None:
    assert isinstance(MyEnumAdjacent.StringTuple(("abc", "abc")), MyEnumAdjacent)
    assert isinstance(MyEnumAdjacent.StringTuple(("abc", "abc")), MyEnumAdjacent.StringTuple)
    assert isinstance(MyEnumAdjacent.Int(123), MyEnumAdjacent.Int)
    assert isinstance(MyEnumAdjacent.Other(OtherEnum1.Int(123)), MyEnumAdjacent.Other)
    assert isinstance(MyEnumAdjacent.Self(MyEnumAdjacent.Int(123)), MyEnumAdjacent.Self)
    assert isinstance(MyEnumAdjacent.NoValue(), MyEnumAdjacent.NoValue)
    assert isinstance(MyEnumAdjacent.Optional(None), MyEnumAdjacent.Optional)

    assert not isinstance(MyEnumAdjacent.Int(123), MyEnumAdjacent.Str)
    assert not isinstance(MyEnumAdjacent.StringTuple(("abc", "abc")), MyEnumAdjacent.Int)
    assert not isinstance(MyEnumAdjacent.Self(MyEnumAdjacent.Int(123)), MyEnumAdjacent.Other)
    assert not isinstance(MyEnumAdjacent.NoValue(), MyEnumAdjacent.Optional)
    assert not isinstance(MyEnumAdjacent.NoValue(), MyEnumAdjacent.Self)


def test_int() -> None:
    model = MyEnumAdjacent.Int(1)
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_str() -> None:
    model = MyEnumAdjacent.Str("str")
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_list() -> None:
    model = MyEnumAdjacent.List(["list"])
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_tuple() -> None:
    model = MyEnumAdjacent.StringTuple(("str", "str2"))
    value = model.model_dump_json()
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored
    assert "just_str_tuple" == json.loads(value)["tag"]


def test_nested_enum() -> None:
    model = MyEnumAdjacent.Other(OtherEnum1.D(TD1(b="123")))
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_dataclass() -> None:
    model = MyEnumAdjacent.DataClass(TDataClass1(a=1))
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_model() -> None:
    model = MyEnumAdjacent.Model(TModel1(b="test_model"))
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_typed_dict() -> None:
    model = MyEnumAdjacent.TypedDict(TD1(b="td"))
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_dict() -> None:
    model = MyEnumAdjacent.Dict({"a": "1", "b": "2"})
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_optional() -> None:
    model = MyEnumAdjacent.Optional(None)
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty() -> None:
    model = MyEnumAdjacent.NoValue()
    restored: MyEnumAdjacent[Any] = MyEnumAdjacent.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty_serialization_compatibility() -> None:
    value = MyEnumAdjacent.NoValue().model_dump_json()
    assert value == '{"tag":"NoValue"}'

    assert (
            MyEnumAdjacent({"tag": "NoValue"}) ==
            MyEnumAdjacent({"tag": "NoValue", "payload": None}) ==
            MyEnumAdjacent(**{"tag": "NoValue", "payload": None}) ==
            MyEnumAdjacent.NoValue() ==
            MyEnumAdjacent.model_validate_json('{"tag":"NoValue","payload":null}') ==
            MyEnumAdjacent.model_validate_json('{"tag":"NoValue"}')
    )
