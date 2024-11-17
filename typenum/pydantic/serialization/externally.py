import inspect
import typing

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

from typenum.core import TypEnumContent, NoValue
from typenum.pydantic.serialization.tagged import TaggedSerialization

if typing.TYPE_CHECKING:
    from ..core import TypEnumPydantic  # type: ignore

__all__ = [
    "ExternallyTagged",
]


class ExternallyTagged(TaggedSerialization):
    def __get_pydantic_core_schema__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from typenum.pydantic.core import TypEnumPydantic

        json_schema_attrs = {}
        other_schemas = []
        for attr in kls.__variants__.values():
            enum_variant: type[TypEnumPydantic[TypEnumContent]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)

            is_typenum_variant = (
                    inspect.isclass(enum_variant.__content_type__) and
                    issubclass(enum_variant.__content_type__, TypEnumPydantic)
            )

            item_schema: core_schema.CoreSchema
            if is_typenum_variant or enum_variant.__content_type__ is NoValue:
                if enum_variant.__content_type__ is NoValue:
                    other_schemas.append(core_schema.str_schema(pattern=attr))
                    continue
                else:
                    kls_: type = enum_variant.__content_type__  # type: ignore
                    schema_definition = core_schema.definition_reference_schema(f"{kls_.__name__}:{id(kls_)}")
                    item_schema = core_schema.definitions_schema(
                        schema=schema_definition,
                        definitions=[
                            core_schema.any_schema(ref=f"{kls_.__name__}:{id(kls_)}")
                        ],
                    )

            else:
                item_schema = handler.generate_schema(enum_variant.__content_type__)

            json_schema_attrs[attr] = core_schema.typed_dict_field(item_schema, required=False)

        schemas = [core_schema.typed_dict_schema(json_schema_attrs), *other_schemas]

        return core_schema.json_or_python_schema(
            json_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                core_schema.union_schema([*schemas]),
            ),
            python_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                core_schema.union_schema([*schemas, core_schema.any_schema()]),
            ),
            serialization=core_schema.wrap_serializer_function_ser_schema(
                kls.__pydantic_serialization__
            ),
            ref=f"{kls.__name__}:{id(kls)}"
        )

    def __python_value_restore__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        from typenum.pydantic.core import TypEnumPydantic

        if isinstance(input_value, TypEnumPydantic):
            return input_value

        if isinstance(input_value, str):
            input_value = {input_value: None}

        for attr, value in input_value.items():
            attr = kls.__names_deserialization__.get(attr, attr)
            return getattr(kls, attr).__variant_constructor__(value, info)

    def __pydantic_serialization__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        attr = model.__variant_name__
        attr = kls.__names_serialization__.get(attr, attr)

        if model.__content_type__ is NoValue:
            return attr
        elif isinstance(model.value, kls):
            content = kls.__pydantic_serialization__(model.value, serializer)
        else:
            content = serializer(model.value)

        return {attr: content}
