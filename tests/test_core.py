import dataclasses
from typing import TypedDict, Any

from enumetyped import Enumetyped, Empty, Content


class TD(TypedDict):
    a: str


@dataclasses.dataclass
class DT:
    b: str


class SimpleEnum(Enumetyped[Content]):
    EmptyVar: type["SimpleEnum[Empty]"]
    Int: type["SimpleEnum[int]"]
    TDVar: type["SimpleEnum[TD]"]
    DTVar: type["SimpleEnum[DT]"]
    Self: type["SimpleEnum[SimpleEnum[Any]]"]


def test_instance_checking_empty() -> None:
    assert isinstance(SimpleEnum.EmptyVar(), SimpleEnum)
    assert isinstance(SimpleEnum.EmptyVar(), SimpleEnum.EmptyVar)


def test_instance_checking_empty_ellipsis() -> None:
    assert isinstance(SimpleEnum.EmptyVar(...), SimpleEnum)
    assert isinstance(SimpleEnum.EmptyVar(...), SimpleEnum.EmptyVar)


def test_instance_checking_simple() -> None:
    assert isinstance(SimpleEnum.Int(123), SimpleEnum)
    assert isinstance(SimpleEnum.Int(123), SimpleEnum.Int)


def test_instance_checking_typed_dict() -> None:
    assert isinstance(SimpleEnum.TDVar(TD(a="test")), SimpleEnum)
    assert isinstance(SimpleEnum.TDVar(TD(a="test")), SimpleEnum.TDVar)


def test_instance_checking_data_class() -> None:
    assert isinstance(SimpleEnum.DTVar(DT(b="test")), SimpleEnum)
    assert isinstance(SimpleEnum.DTVar(DT(b="test")), SimpleEnum.DTVar)


def test_instance_checking_recursive() -> None:
    assert isinstance(SimpleEnum.Self(SimpleEnum.DTVar(DT(b="test"))), SimpleEnum)
    assert isinstance(SimpleEnum.Self(SimpleEnum.DTVar(DT(b="test"))), SimpleEnum.Self)


def test_pattern_matching() -> None:
    a: bool = False

    match SimpleEnum.Int(1):
        case SimpleEnum.Int(2):
            a = False
        case SimpleEnum.Int(1):
            a = True
        case _:
            a = False

    assert a

    match SimpleEnum.Int(1):
        case SimpleEnum.Int(2):
            a = False
        case SimpleEnum.Int():
            a = True
        case _:
            a = False

    assert a


def test_equality() -> None:
    assert SimpleEnum.Int(1) == SimpleEnum.Int(1)
    assert SimpleEnum.Int(1) != SimpleEnum.Int(2)
    assert SimpleEnum.Int(1) != SimpleEnum.EmptyVar()
