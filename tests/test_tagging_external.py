import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel
from typing_extensions import Annotated, TypedDict

from enumetyped import Content
from enumetyped import Empty
from enumetyped.pydantic import FieldMetadata, EnumetypedPydantic, Rename
from enumetyped.pydantic.serialization.external import AlwaysSerializeToDict


@dataclass
class TDataClass:
    a: int


class TModel(BaseModel):
    b: str


class TD(TypedDict):
    b: str


class SimpleEnum(EnumetypedPydantic[Empty]):
    V1: type["SimpleEnum"]
    V2: type["SimpleEnum"]


class OtherEnum(EnumetypedPydantic[Content]):
    D: type["OtherEnum[TD]"]
    C: type["OtherEnum[TDataClass]"]
    Int: type["OtherEnum[int]"]


class MyEnum(EnumetypedPydantic[Content]):
    # MyEnum.Int(123)
    Int: type["MyEnum[int]"]

    # MyEnum.Str(123)
    Str: type["MyEnum[str]"]

    # MyEnum.Str(OtherEnum.Int(1))
    Other: type["MyEnum[OtherEnum[Any]]"]  # any from OtherEnum variants

    # MyEnum.Str(MyEnum.Int(1)) | MyEnum.Str(MyEnum.Str(1))
    Self: type["MyEnum[MyEnum[Any]]"]  # any from self variants

    # MyEnum.OnlySelf(...) - any parameters skipped
    NoValue: type["MyEnum[Empty]"]

    # MyEnum.OnlySelf2(None)
    Optional: type["MyEnum[Optional[bool]]"]

    # MyEnum.List(["1", "2", "3"])
    List: type["MyEnum[list[str]]"]

    # MyEnum.Dict({"key": "value"})
    Dict: type["MyEnum[dict[str, str]]"]
    # TypedDict: type["MyEnum[{"b": str}]"]
    TypedDict: type["MyEnum[TD]"]  # python does not have inline TypedDict now

    # MyEnum.DC(TestDataClass(a=1))
    DataClass: type["MyEnum[TDataClass]"]

    # MyEnum.Model(TestModel(b="2"))
    Model: type["MyEnum[TModel]"]

    # MyEnum.StrTuple(("1", "2")))
    StringTuple: Annotated[type["MyEnum[tuple[str, str]]"], FieldMetadata(rename="just_str_tuple")]

    # or use typenum.pydantic.Rename
    StrTuple: Annotated[type["MyEnum[tuple[str, str]]"], Rename("some_other_name")]


def test_isinstance() -> None:
    assert isinstance(MyEnum.StringTuple(("abc", "abc")), MyEnum)
    assert isinstance(MyEnum.StringTuple(("abc", "abc")), MyEnum.StringTuple)
    assert isinstance(MyEnum.Int(123), MyEnum.Int)
    assert isinstance(MyEnum.Other(OtherEnum.Int(123)), MyEnum.Other)
    assert isinstance(MyEnum.Self(MyEnum.Int(123)), MyEnum.Self)
    assert isinstance(MyEnum.NoValue(), MyEnum.NoValue)
    assert isinstance(MyEnum.Optional(None), MyEnum.Optional)

    assert not isinstance(MyEnum.Int(123), MyEnum.Str)
    assert not isinstance(MyEnum.StringTuple(("abc", "abc")), MyEnum.Int)
    assert not isinstance(MyEnum.Self(MyEnum.Int(123)), MyEnum.Other)
    assert not isinstance(MyEnum.NoValue(), MyEnum.Optional)
    assert not isinstance(MyEnum.NoValue(), MyEnum.Self)


def test_int() -> None:
    model = MyEnum.Int(1)
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_str() -> None:
    model = MyEnum.Str("str")
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_list() -> None:
    model = MyEnum.List(["list"])
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_tuple() -> None:
    model = MyEnum.StringTuple(("str", "str2"))
    value = model.model_dump_json()
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored
    assert "just_str_tuple" in json.loads(value)


def test_nested_enum() -> None:
    model = MyEnum.Other(OtherEnum.D(TD(b="123")))
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_dataclass() -> None:
    model = MyEnum.DataClass(TDataClass(a=1))
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_model() -> None:
    model = MyEnum.Model(TModel(b="test_model"))
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_typed_dict() -> None:
    model = MyEnum.TypedDict(TD(b="td"))
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_dict() -> None:
    model = MyEnum.Dict({"a": "1", "b": "2"})
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_optional() -> None:
    model = MyEnum.Optional(None)
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty() -> None:
    model = MyEnum.NoValue()
    restored: MyEnum[Any] = MyEnum.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty_serialization_compatibility() -> None:
    value = MyEnum.NoValue().model_dump_json()
    assert value == '"NoValue"'

    t = AlwaysSerializeToDict.set(True)
    value = MyEnum.NoValue().model_dump_json()
    assert value == '{"NoValue":null}'
    AlwaysSerializeToDict.reset(t)

    assert (
            MyEnum("NoValue") ==
            MyEnum({"NoValue": None}) ==
            MyEnum(**{"NoValue": None}) ==
            MyEnum.NoValue() ==
            MyEnum.model_validate_json('{"NoValue":null}') ==
            MyEnum.model_validate_json('"NoValue"')
    )
