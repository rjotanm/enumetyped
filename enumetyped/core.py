import types
import typing

__all__ = [
    "NoValue",
    "TypEnum",
    "TypEnumContent",
    "TypEnumMeta",
]

import typing_extensions

from annotated_types import BaseMetadata
from typing_extensions import Annotated

TypEnumContent = typing.TypeVar("TypEnumContent")


NoValue = types.EllipsisType


class TypEnumMeta(type):
    __full_variant_name__: str
    __variant_name__: str

    __content_type__: typing.Union[str, type[typing.Any]]

    __variants__: dict[type['_TypEnum[typing.Any]'], str]

    __is_variant__: bool = False

    def __new__(
            cls,
            cls_name: str,
            bases: tuple[typing.Any],
            class_dict: dict[str, typing.Any],
    ) -> typing.Any:
        enum_class = super().__new__(cls, cls_name, bases, class_dict)
        if enum_class.__annotations__.get("__abstract__"):
            return enum_class

        if enum_class.__is_variant__:
            return enum_class
        else:
            enum_class.__variants__ = dict()

        enum_class.__full_variant_name__ = cls_name
        enum_class.__variant_name__ = cls_name

        annotation: typing.Union[type[Annotated[typing.Any, BaseMetadata]], type]
        for attr, annotation in enum_class.__annotations__.items():
            if not hasattr(annotation, "__args__"):
                continue

            if (__origin__ := getattr(annotation, "__origin__", None)) and annotation.__name__ == "Annotated":
                origin = typing.get_args(__origin__)[0]
            else:
                is_type = isinstance(annotation, types.GenericAlias) and annotation.__name__ == "type"
                if not is_type:
                    continue

                origin = typing.get_args(annotation)[0]

            split = origin[:-1].split("[", maxsplit=1)

            content_type: str | type[typing.Any]
            if len(split) == 1:
                content_type = NoValue
            else:
                left, right = split
                if left != enum_class.__name__:
                    continue

                if right.split("[", maxsplit=1)[0] == enum_class.__name__:
                    content_type = enum_class
                else:
                    try:
                        content_type = eval(right)
                    except NameError:
                        content_type = right

            try:
                variant_base = enum_class[content_type]  # type: ignore
            except TypeError:
                # When enum is non-generic, like this
                #
                # class SimpleEnum(TypEnum):
                #     V: type["SimpleEnum"]
                #
                variant_base = enum_class

            class _EnumVariant(variant_base):  # type: ignore
                __is_variant__ = True

            _EnumVariant.__name__ = _EnumVariant.__full_variant_name__ = f"{enum_class.__name__}.{attr}"
            _EnumVariant.__variant_name__ = attr
            _EnumVariant.__content_type__ = content_type

            enum_class.__variants__[_EnumVariant] = attr

            setattr(enum_class, attr, _EnumVariant)

        return enum_class

    def __repr__(self) -> str:
        return getattr(self, "__full_variant_name__", self.__class__.__name__)


class _TypEnum(typing.Generic[TypEnumContent], metaclass=TypEnumMeta):
    __match_args__ = ("value",)

    __full_variant_name__: typing.ClassVar[str]
    __variant_name__: typing.ClassVar[str]

    __content_type__: typing.ClassVar[typing.Union[str, type[typing.Any]]]

    __variants__: typing.ClassVar[dict[type['_TypEnum[typing.Any]'], str]]

    __is_variant__: typing.ClassVar[bool] = False

    __abstract__: typing_extensions.Never

    value: typing.Optional[TypEnumContent]

    def __init__(self, value: TypEnumContent):
        if self.__content_type__ is NoValue:
            self.value = None
        else:
            self.value = value

    def __repr__(self) -> str:
        if self.__content_type__ is NoValue:
            return f"{self.__full_variant_name__}()"
        return f"{self.__full_variant_name__}({self.value.__repr__()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _TypEnum):
            return False

        return self.__class__ == other.__class__ and self.value == other.value


class TypEnum(_TypEnum[TypEnumContent]):
    __abstract__: typing_extensions.Never
