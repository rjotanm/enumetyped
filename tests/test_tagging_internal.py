from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from typing_extensions import TypedDict

from enumetyped import Content
from enumetyped import Empty
from enumetyped.pydantic import EnumetypedPydantic


@dataclass
class TDataClass2:
    a: int


class TModel2(BaseModel):
    b: str


class TD3(TypedDict):
    b: str


class SimpleEnum4(EnumetypedPydantic[Empty]):
    V1: type["SimpleEnum4"]
    V2: type["SimpleEnum4"]


class OtherEnum5(EnumetypedPydantic[Content]):
    D: type["OtherEnum5[TD3]"]
    C: type["OtherEnum5[TDataClass2]"]
    Int: type["OtherEnum5[int]"]


class MyEnumInternal(EnumetypedPydantic[Content], variant="tag"):
    # MyEnum.Str(OtherEnum.Int(1))
    Other: type["MyEnumInternal[OtherEnum5[Any]]"]  # any from OtherEnum variants

    # MyEnum.Str(MyEnum.Int(1)) | MyEnum.Str(MyEnum.Str(1))
    Self: type["MyEnumInternal[MyEnumInternal[Any]]"]  # any from self variants

    # MyEnum.OnlySelf(...) - any parameters skipped
    NoValue: type["MyEnumInternal[Empty]"]

    # TypedDict: type["MyEnum[{"b": str}]"]
    TypedDict: type["MyEnumInternal[TD3]"]  # python does not have inline TypedDict now

    # MyEnum.DC(TestDataClass(a=1))
    DataClass: type["MyEnumInternal[TDataClass2]"]

    # MyEnum.Model(TestModel(b="2"))
    Model: type["MyEnumInternal[TModel2]"]


def test_isinstance() -> None:
    assert isinstance(MyEnumInternal.Other(OtherEnum5.Int(123)), MyEnumInternal.Other)
    assert isinstance(MyEnumInternal.NoValue(), MyEnumInternal.NoValue)
    assert not isinstance(MyEnumInternal.NoValue(), MyEnumInternal.Self)


def test_nested_enum() -> None:
    model = MyEnumInternal.Other(OtherEnum5.D(TD3(b="123")))
    restored: MyEnumInternal[Any] = MyEnumInternal.model_validate_json(model.model_dump_json())
    assert model == restored


def test_dataclass() -> None:
    model = MyEnumInternal.DataClass(TDataClass2(a=1))
    restored: MyEnumInternal[Any] = MyEnumInternal.model_validate_json(model.model_dump_json())
    assert model == restored


def test_model() -> None:
    model = MyEnumInternal.Model(TModel2(b="test_model"))
    restored: MyEnumInternal[Any] = MyEnumInternal.model_validate_json(model.model_dump_json())
    assert model == restored


def test_typed_dict() -> None:
    model = MyEnumInternal.TypedDict(TD3(b="td"))
    restored: MyEnumInternal[Any] = MyEnumInternal.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty() -> None:
    model = MyEnumInternal.NoValue()
    restored: MyEnumInternal[Any] = MyEnumInternal.model_validate_json(model.model_dump_json())
    assert model == restored


def test_empty_serialization_compatibility() -> None:
    value = MyEnumInternal.NoValue().model_dump_json()
    assert value == '{"tag":"NoValue"}'

    assert (
            MyEnumInternal({"tag": "NoValue"}) ==
            MyEnumInternal({"tag": "NoValue", "payload": None}) ==
            MyEnumInternal(**{"tag": "NoValue", "payload": None}) ==
            MyEnumInternal.NoValue() ==
            MyEnumInternal.model_validate_json('{"tag":"NoValue","payload":null}') ==
            MyEnumInternal.model_validate_json('{"tag":"NoValue"}')
    )
