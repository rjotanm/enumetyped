import inspect
import typing

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

from enumetyped.core import TypEnumContent, NoValue
from enumetyped.pydantic.serialization.tagged import TaggedSerialization

if typing.TYPE_CHECKING:
    from ..core import TypEnumPydantic  # type: ignore


__all__ = [
    "AdjacentlyTagged",
]


class AdjacentlyTagged(TaggedSerialization):
    __variant_tag__: str
    __content_tag__: str

    def __init__(self, variant: str, content: str):
        self.__variant_tag__ = variant
        self.__content_tag__ = content

    def __get_pydantic_core_schema__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from enumetyped.pydantic.core import TypEnumPydantic

        json_schemas: list[core_schema.CoreSchema] = []
        for attr in kls.__variants__.values():
            enum_variant: type[TypEnumPydantic[TypEnumContent]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)
            variant_schema = core_schema.typed_dict_field(core_schema.str_schema(pattern=attr))
            is_enumetyped_variant = (
                    inspect.isclass(enum_variant.__content_type__) and
                    issubclass(enum_variant.__content_type__, TypEnumPydantic)
            )

            schema = {
                self.__variant_tag__: variant_schema,
            }

            if is_enumetyped_variant or enum_variant.__content_type__ is NoValue:
                if is_enumetyped_variant:
                    kls_: type = enum_variant.__content_type__  # type: ignore
                    schema_definition = core_schema.definition_reference_schema(f"{kls_.__name__}:{id(kls_)}")
                    value_schema = core_schema.typed_dict_field(core_schema.definitions_schema(
                        schema=schema_definition,
                        definitions=[
                            core_schema.any_schema(ref=f"{kls_.__name__}:{id(kls_)}")
                        ],
                    ))

                    schema[self.__content_tag__] = value_schema
            else:
                value_schema = core_schema.typed_dict_field(handler.generate_schema(enum_variant.__content_type__))
                schema[self.__content_tag__] = value_schema

            json_schemas.append(core_schema.typed_dict_schema(schema))

        return core_schema.json_or_python_schema(
            json_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                core_schema.union_schema([*json_schemas]),
            ),
            python_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                core_schema.union_schema([*json_schemas, core_schema.any_schema()]),
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
        from enumetyped.pydantic.core import TypEnumPydantic

        if isinstance(input_value, TypEnumPydantic):
            return input_value

        type_key = input_value[self.__variant_tag__]
        value = input_value.get(self.__content_tag__, None)
        attr = kls.__names_deserialization__.get(type_key, type_key)
        return getattr(kls, attr).__variant_constructor__(value, info)

    def __pydantic_serialization__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        attr = model.__variant_name__
        attr = kls.__names_serialization__.get(attr, attr)

        result = {self.__variant_tag__: attr}
        if model.__content_type__ is NoValue:
            pass
        elif isinstance(model.value, TypEnumPydantic):
            result[self.__content_tag__] = model.__pydantic_serialization__(model.value, serializer)
        else:
            result[self.__content_tag__] = serializer(model.value)

        return result
