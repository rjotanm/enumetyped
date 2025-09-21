import inspect
import typing

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

from enumetyped.core import Content, Empty
from enumetyped.pydantic.serialization.tagging import Tagging

if typing.TYPE_CHECKING:
    from enumetyped.core import Content
    from enumetyped.pydantic.core import EnumetypedPydantic


__all__ = [
    "AdjacentTagging",
]


class AdjacentTagging(Tagging):
    __variant_tag__: str
    __content_tag__: str

    def __init__(self, variant: str, content: str):
        self.__variant_tag__ = variant
        self.__content_tag__ = content

    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from enumetyped.pydantic.core import EnumetypedPydantic

        schema_ref = f"{kls.__module__}.{kls.__name__}:{id(kls)}"

        json_schemas: list[core_schema.CoreSchema] = []
        for attr in kls.__variants__.values():
            enum_variant: type[EnumetypedPydantic[Content]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)
            variant_schema = core_schema.typed_dict_field(core_schema.str_schema(pattern=attr))
            is_enumetyped_variant = (
                    inspect.isclass(enum_variant.__content_type__) and
                    issubclass(enum_variant.__content_type__, EnumetypedPydantic)
            )

            schema = {
                self.__variant_tag__: variant_schema,
            }

            if is_enumetyped_variant or enum_variant.__content_type__ is Empty:
                if is_enumetyped_variant:
                    schema[self.__content_tag__] = core_schema.typed_dict_field(core_schema.any_schema())
            else:
                value_schema = core_schema.typed_dict_field(handler.generate_schema(enum_variant.__content_type__))
                schema[self.__content_tag__] = value_schema

            json_schemas.append(core_schema.typed_dict_schema(schema))

        result = core_schema.definitions_schema(
            schema=core_schema.definition_reference_schema(schema_ref),
            definitions=[
                core_schema.json_or_python_schema(
                    json_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        core_schema.union_schema(json_schemas),
                    ),
                    python_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        core_schema.union_schema([*json_schemas, core_schema.any_schema()]),
                    ),
                    serialization=core_schema.wrap_serializer_function_ser_schema(
                        kls.__pydantic_serialization__
                    ),
                    ref=schema_ref,
                )
            ]
        )
        return result

    def parse(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
    ) -> typing.Any:
        type_key = input_value[self.__variant_tag__]
        value = input_value.get(self.__content_tag__, None)
        attr = kls.__names_deserialization__.get(type_key, type_key)
        return attr, value

    def __python_value_restore__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        return super().__python_value_restore__(kls, input_value, info)

    def __pydantic_serialization__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        from enumetyped.pydantic.core import EnumetypedPydantic

        attr = model.__variant_name__
        attr = kls.__names_serialization__.get(attr, attr)

        value = model._value  # noqa

        result = {self.__variant_tag__: attr}
        if model.__content_type__ is Empty:
            pass
        elif isinstance(value, EnumetypedPydantic):
            result[self.__content_tag__] = value.__pydantic_serialization__(value, serializer)
        else:
            result[self.__content_tag__] = serializer(value)

        return result
