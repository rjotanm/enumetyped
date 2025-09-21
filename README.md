# Enumetyped

This package provide a way to create typed enumerations.

# Install

- `pip install enumetyped`
- `pip install enumetyped[pydantic]` - install with pydantic `>=2.9`

# Quickstart

#### Without pydantic

```python
from enumetyped import Enumetyped, Empty, Content


class SimpleEnum(Enumetyped[Content]):
    A: type["SimpleEnum[Empty]"]
    Int: type["SimpleEnum[int]"]


# isinstance checking
assert isinstance(SimpleEnum.A(), SimpleEnum)
assert isinstance(SimpleEnum.Int(123), SimpleEnum.Int)
assert not isinstance(SimpleEnum.Int(123), SimpleEnum.A)

# fully pattern-matching
match SimpleEnum.Int(1):
    case SimpleEnum.Int(2):
        a = False
    case SimpleEnum.Int(1):
        a = True
    case SimpleEnum.Int():
        a = True
    case _:
        a = False

assert a
```

#### With pydantic

```python
import typing
from dataclasses import dataclass

from pydantic import BaseModel

from enumetyped import Enumetyped, Content, Empty
from enumetyped.pydantic import EnumetypedPydantic, FieldMetadata, Rename
from typing_extensions import Annotated, TypedDict


class Enum(Enumetyped[Empty]):
    V1: type["Enum"]
    V2: type["Enum"]


@dataclass
class TestDataClass:
    a: int


class TestModel(BaseModel):
    b: str


class TestTypedDict(TypedDict):
    tm: TestModel


class SimpleEnum(EnumetypedPydantic[Empty]):
    V1: type["SimpleEnum"]
    V2: type["SimpleEnum"]


class OtherEnum(EnumetypedPydantic[Content]):
    Int: type["OtherEnum[int]"]
    Int: type["OtherEnum[str]"]


# class MyEnum(EnumetypedPydantic[Content], variant="key", content="value"):  # <- adjacently
# class MyEnum(EnumetypedPydantic[Content], variant="key"):  # <- internally
class MyEnum(EnumetypedPydantic[Content]):  # <- externally, default
    # MyEnum.Int(123)
    Int: type["MyEnum[int]"]

    # MyEnum.Str(123)
    Str: type["MyEnum[str]"]

    # MyEnum.Str(OtherEnum.Int(1))
    Other: type["MyEnum[OtherEnum[Any]]"]  # any from OtherEnum variants

    # MyEnum.Str(MyEnum.Int(1)) | MyEnum.Str(MyEnum.Str(1))
    Self: type["MyEnum[MyEnum[Any]]"]  # any from self variants

    # MyEnum.OnlySelf(...) - any parameters skipped, serialized just by name
    NoValue: type["MyEnum[NoValue]"]

    # MyEnum.OnlySelf2(None)
    Optional: type["MyEnum[Optional[bool]]"]

    # MyEnum.List(["1", "2", "3"])
    List: type["MyEnum[list[str]]"]

    # MyEnum.Dict({"key": "value"})
    Dict: type["MyEnum[dict[str, str]]"]
    # TypedDict: type["MyEnum[{"b": str}]"]
    TypedDict: type["MyEnum[TestD]"]  # python doesn`t have inline TypedDict now

    # MyEnum.DC(TestDataClass(a=1))
    DataClass: type["MyEnum[TestDataClass]"]

    # MyEnum.Model(TestModel(b="2"))
    Model: type["MyEnum[TestModel]"]

    # MyEnum.StrTuple(("1", "2")))
    StringTuple: Annotated[type["MyEnum[tuple[str, str]]"], FieldMetadata(rename="just_str_tuple")]
    # or use enumetyped.pydantic.Rename
    # StrTuple: Annotated[type["MyEnum[tuple[str, str]]"], Rename("some_other_name")]

    # MyEnum.DeepAndDeeper([{"a": [(1, MyEnum.Int(2))]}])
    DeepAndDeeper: type["MyEnum[list[dict[str, list[tuple[int, MyEnum]]]]]"]

class FinModel(BaseModel):
    enum: MyEnum


def dump_and_load(e: MyEnum):
    # Can use in other model
    #
    # model = FinModel(enum=e)
    # json_ = model.model_dump_json()
    # print(json_)
    # restored = FinModel.model_validate_json(json_)
    # assert model == restored
    
    json_ = e.model_dump_json()
    print(json_)
    restored = MyEnum.model_validate_json(json_)
    assert e == restored


# externally -> {"enum":{"Int":1}} 
# adjacently -> {"enum":{"key":"Int","value":1}}
# internally -> not supported
dump_and_load(MyEnum.Int(1))

# externally -> {"enum":{"Str":"str"}}
# adjacently -> {"enum":{"key":"Str","value":"str"}}
# internally -> not supported
dump_and_load(MyEnum.Str("str"))

# externally -> {"enum":{"List":["list"]}}
# adjacently -> {"enum":{"key":"List","value":["list"]}}
# internally -> not supported
dump_and_load(MyEnum.List(["list"]))

# externally -> {"enum":{"just_str_tuple":["str","str2"]}} 
# adjacently -> {"enum":{"key":"just_str_tuple","value":["str","str2"]}}
# internally -> not supported
dump_and_load(MyEnum.StringTuple(("str", "str2")))

# externally -> {"enum":{"Self":{"Int":1}}} 
# adjacently -> {"enum":{"key":"Self","value":{"key":"Int","value":1}}}
# internally -> not supported
dump_and_load(MyEnum.Self(MyEnum.Int(1)))

# externally -> {"enum":{"DC":{"a":1}}} 
# adjacently -> {"enum":{"key":"DC","value":{"a":1}}}
# internally -> {"enum":{"key":"DC","a":1}}}
# internally -> may fall with "was never filled on some pydantic versions"
dump_and_load(MyEnum.DataClass(TestDataClass(a=1)))

# externally -> {"enum":{"Model":{"b":"test_model"}}} 
# adjacently -> {"enum":{"key":"Model","value":{"b":"test_model"}}}
# internally -> {"enum":{"key":"Model", "b":"test_model"}}
dump_and_load(MyEnum.Model(TestModel(b="test_model")))

# externally -> {"enum":{"TypedDict":{"tm":{"b":"test_model"}}}} 
# adjacently -> {"enum":{"key":"TypedDict","value":{"tm":{"b":"test_model"}}}}
# internally -> {"enum":{"key":"TypedDict","tm":{"b":"test_model"}}}
# internally -> may fall with "was never filled on some pydantic versions"
dump_and_load(MyEnum.TypedDict(TestTypedDict(tm=TestModel(b="test_model"))))

# externally -> {"enum":{"Dict":{"a":"1","b":"2"}}} 
# adjacently -> {"enum":{"key":"Dict","value":{"a":"1","b":"2"}}}
# internally -> not supported
dump_and_load(MyEnum.Dict({"a": "1", "b": "2"}))

# externally -> {"enum":"NoValue"}
# adjacently -> {"enum":{"key":"NoValue"}}
# internally -> {"enum":{"key":"NoValue"}}
dump_and_load(MyEnum.NoValue())

# externally -> {"enum":{"Optional":null}} 
# adjacently -> {"enum":{"key":"Optional","value":null}}
# internally -> not supported
dump_and_load(MyEnum.Optional(None))

# externally -> {"enum":{"DeepAndDeeper":[{"a":[[1,{"Int":2}]]}]}}
# adjacently -> {"enum":{"key":"DeepAndDeeper","value":[{"a":[[1,{"key":"Int","value":2}]]}]}}
# internally -> not supported
dump_and_load(MyEnum.DeepAndDeeper([{"a": [(1, MyEnum.Int(2))]}]))
```

#### Other

 - [Compatibility](docs/compatibility.md)
 - [Limitations](docs/limitations.md)