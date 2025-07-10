import importlib
import inspect
import typing
from dataclasses import dataclass
import pydantic as pydantic_
import typing_extensions
from annotated_types import GroupedMetadata, BaseMetadata
from pydantic import TypeAdapter
from pydantic.json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaMode
from pydantic.main import IncEx
from pydantic_core import core_schema
from pydantic_core.core_schema import ValidationInfo, SerializerFunctionWrapHandler

from enumetyped.core import EnumetypedMeta, Content, Enumetyped

__all__ = [
    "Rename",
    "FieldMetadata",
    "EnumetypedPydantic",
    "EnumetypedPydanticMeta",
    "eval_content_type",
]

from enumetyped.pydantic.serialization import AdjacentTagging, InternalTagging, ExternalTagging
from enumetyped.pydantic.serialization.tagging import Tagging


@dataclass(frozen=True, slots=True)
class Rename(BaseMetadata):
    value: str


@dataclass
class FieldMetadata(GroupedMetadata):
    rename: typing.Optional[str] = None

    def __iter__(self) -> typing.Iterator[BaseMetadata]:
        if self.rename is not None:
            yield Rename(self.rename)


def eval_content_type(cls: type['EnumetypedPydantic[Content]']) -> type:
    # Eval annotation into real object
    base = cls.__orig_bases__[0]  # type: ignore
    module = importlib.import_module(base.__module__)
    return eval(cls.__content_type__, module.__dict__)  # type: ignore


class EnumetypedPydanticMeta(EnumetypedMeta):
    __tagging__: Tagging

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
            enum_class.__serialization__ = AdjacentTagging(variant, content)
        elif variant is not None:
            enum_class.__serialization__ = InternalTagging(variant)
        else:
            enum_class.__serialization__ = ExternalTagging()

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


class EnumetypedPydantic(Enumetyped[Content], metaclass=EnumetypedPydanticMeta):
    __abstract__: typing_extensions.Never

    __names_serialization__: typing.ClassVar[dict[str, str]]
    __names_deserialization__: typing.ClassVar[dict[str, str]]

    __tagging__: typing.ClassVar[Tagging]

    _type_adapter: typing.Optional[TypeAdapter[typing_extensions.Self]] = None

    @classmethod
    def content_type(cls) -> type:
        # Resolve types when __content_type__ declare after cls declaration
        if isinstance(cls.__content_type__, str):
            cls.__content_type__ = eval_content_type(cls)
        return cls.__content_type__

    @classmethod
    def __variant_constructor__(
            cls: type["EnumetypedPydantic[Content]"],
            value: typing.Any,
            info: ValidationInfo,
    ) -> "EnumetypedPydantic[Content]":
        if inspect.isclass(cls.content_type()) and issubclass(cls.content_type(), EnumetypedPydantic):
            value = cls.__python_value_restore__(value, info)

        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
            cls: type["EnumetypedPydantic[Content]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return cls.__tagging__.__get_pydantic_core_schema__(cls, source_type, handler)  # type: ignore

    @classmethod
    def __python_value_restore__(
            cls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        return cls.__tagging__.__python_value_restore__(cls, input_value, info)  # type: ignore

    @classmethod
    def __pydantic_serialization__(
            cls: type["EnumetypedPydantic[Content]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        return cls.__tagging__.__pydantic_serialization__(cls, model, serializer)  # type: ignore

    @classmethod
    def adapter(cls) -> TypeAdapter[typing_extensions.Self]:
        if cls._type_adapter is None:
            cls._type_adapter = TypeAdapter(cls)
        return cls._type_adapter

    def model_dump(
        self,
        *,
        mode: typing.Literal['json', 'python'] = 'python',
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: typing.Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | typing.Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
    ) -> dict[str, typing.Any]:
        return self.adapter().dump_python(  # type: ignore
            self,
            mode=mode,
            by_alias=by_alias,
            include=include,
            exclude=exclude,
            context=context,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: typing.Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | typing.Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
    ) -> str:
        return self.adapter().dump_json(
            self,
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        ).decode()

    @classmethod
    def json_schema(
        cls,
        *,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, typing.Any]:
        return cls.adapter().json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
        )

    @classmethod
    def model_validate(
        cls,
        obj: typing.Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_python(obj, strict=strict, from_attributes=from_attributes, context=context)

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_json(json_data, strict=strict, context=context)

    @classmethod
    def model_validate_strings(
        cls,
        obj: typing.Any,
        *,
        strict: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_strings(obj, strict=strict, context=context)

