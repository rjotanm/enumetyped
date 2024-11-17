import importlib
import inspect
import typing
import pydantic as pydantic_

from dataclasses import dataclass

import typing_extensions
from annotated_types import GroupedMetadata, BaseMetadata
from pydantic_core import core_schema
from pydantic_core.core_schema import ValidationInfo, SerializerFunctionWrapHandler

from typenum.core import TypEnumMeta, _TypEnum, TypEnumContent

__all__ = [
    "Rename",
    "FieldMetadata",
    "TypEnumPydantic",
    "TypEnumPydanticMeta",
    "eval_content_type",
]

from typenum.pydantic.serialization import AdjacentlyTagged, InternallyTagged, ExternallyTagged
from typenum.pydantic.serialization.tagged import TaggedSerialization


@dataclass(frozen=True, slots=True)
class Rename(BaseMetadata):
    value: str


@dataclass
class FieldMetadata(GroupedMetadata):
    rename: typing.Optional[str] = None

    def __iter__(self) -> typing.Iterator[BaseMetadata]:
        if self.rename is not None:
            yield Rename(self.rename)


def eval_content_type(cls: type['TypEnumPydantic[TypEnumContent]']) -> type:
    # Eval annotation into real object
    base = cls.__orig_bases__[0]  # type: ignore
    module = importlib.import_module(base.__module__)
    return eval(cls.__content_type__, module.__dict__)  # type: ignore


class TypEnumPydanticMeta(TypEnumMeta):
    __serialization__: TaggedSerialization

    def __new__(
            cls,
            cls_name: str,
            bases: tuple[typing.Any],
            class_dict: dict[str, typing.Any],
            variant: typing.Optional[str] = None,
            content: typing.Optional[str] = None,
    ) -> typing.Any:
        enum_class = super().__new__(cls, cls_name, bases, class_dict)
        if enum_class.__annotations__.get("__abstract__"):
            return enum_class

        enum_class.__full_variant_name__ = cls_name
        enum_class.__variant_name__ = cls_name

        if enum_class.__is_variant__:
            return enum_class

        enum_class.__names_serialization__ = dict()
        enum_class.__names_deserialization__ = dict()

        if variant is not None and content is not None:
            enum_class.__serialization__ = AdjacentlyTagged(variant, content)
        elif variant is not None:
            enum_class.__serialization__ = InternallyTagged(variant)
        else:
            enum_class.__serialization__ = ExternallyTagged()

        annotation: typing.Union[type[typing_extensions.Annotated[typing.Any, BaseMetadata]], type]
        for attr, annotation in enum_class.__annotations__.items():
            if not hasattr(annotation, "__args__"):
                continue

            enum_variant = getattr(enum_class, attr)
            if isinstance(enum_variant.__content_type__, str):
                try:
                    enum_variant.__content_type__ = eval_content_type(enum_variant)
                except NameError:
                    ...

            if isinstance(annotation, typing._AnnotatedAlias):  # type: ignore
                metadata: list[typing.Union[BaseMetadata, GroupedMetadata]] = []
                for v in annotation.__metadata__:
                    if isinstance(v, FieldMetadata):
                        metadata.extend(v)
                    else:
                        metadata.append(v)

                for __meta__ in metadata:
                    if isinstance(__meta__, Rename):
                        if __meta__.value in enum_class.__names_deserialization__:
                            raise ValueError(f"{cls_name}: Two or many field renamed to `{__meta__.value}`")

                        enum_class.__names_serialization__[attr] = __meta__.value
                        enum_class.__names_deserialization__[__meta__.value] = attr

        return enum_class


class TypEnumPydantic(_TypEnum[TypEnumContent], metaclass=TypEnumPydanticMeta):
    __abstract__: typing_extensions.Never

    __names_serialization__: typing.ClassVar[dict[str, str]]
    __names_deserialization__: typing.ClassVar[dict[str, str]]

    __serialization__: typing.ClassVar[TaggedSerialization]

    @classmethod
    def __variant_constructor__(
            cls: type["TypEnumPydantic[TypEnumContent]"],
            value: typing.Any,
            info: ValidationInfo,
    ) -> "TypEnumPydantic[TypEnumContent]":
        # Resolve types when __content_type__ declare after cls declaration
        __content_type__ = cls.__content_type__
        if isinstance(__content_type__, str):
            __content_type__ = eval_content_type(cls)

        if inspect.isclass(__content_type__) and issubclass(__content_type__, TypEnumPydantic):
            value = cls.__python_value_restore__(value, info)

        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
            cls: type["TypEnumPydantic[TypEnumContent]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return cls.__serialization__.__get_pydantic_core_schema__(cls, source_type, handler)

    @classmethod
    def __python_value_restore__(
            cls: type["TypEnumPydantic[TypEnumContent]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        return cls.__serialization__.__python_value_restore__(cls, input_value, info)

    @classmethod
    def __pydantic_serialization__(
            cls: type["TypEnumPydantic[TypEnumContent]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        return cls.__serialization__.__pydantic_serialization__(cls, model, serializer)
