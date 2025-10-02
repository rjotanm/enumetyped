import inspect
import typing

import pydantic
import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

from enumetyped.core import Empty, Content
from enumetyped.pydantic.serialization.tagging import Tagging

if typing.TYPE_CHECKING:
    from enumetyped.core import Content
    from enumetyped.pydantic.core import EnumetypedPydantic

__all__ = [
    "InternalTagging",
]


class InternalTagging(Tagging):
    __variant_tag__: str

    def __init__(self, variant: str):
        self.__variant_tag__ = variant

    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        # TODO: simplify

        from enumetyped.pydantic.core import EnumetypedPydantic

        schema_ref = f"{kls.__module__}.{kls.__name__}:{id(kls)}"

        json_schemas: dict[str, core_schema.CoreSchema] = {}
        for attr in kls.__variants__.values():
            enum_variant: type[EnumetypedPydantic[Content]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)

            item_schema: typing.Optional[CoreSchema] = None
            if enum_variant.__content_type__ is Empty:
                item_schema = core_schema.dict_schema()
            else:
                is_enumetyped_variant = (
                        inspect.isclass(enum_variant.__content_type__) and
                        issubclass(enum_variant.__content_type__, EnumetypedPydantic)
                )
                if is_enumetyped_variant:
                    kls_: type = enum_variant.__content_type__  # type: ignore
                    child_schema_ref = f"{kls_.__module__}.{kls_.__name__}:{id(kls_)}"
                    if child_schema_ref == schema_ref:
                        item_schema = core_schema.definition_reference_schema(schema_ref)

                if item_schema is None:
                    item_schema = handler.generate_schema(enum_variant.__content_type__)

            json_schemas[attr] = core_schema.json_or_python_schema(
                json_schema=core_schema.with_info_after_validator_function(
                    getattr(kls, attr).__python_value_restore__,
                    item_schema,
                ),
                python_schema=core_schema.with_info_after_validator_function(
                    getattr(kls, attr).__python_value_restore__,
                    core_schema.union_schema([item_schema, core_schema.any_schema()])
                ),
            )

        json_schema = core_schema.tagged_union_schema(
            choices=json_schemas,
            discriminator=self.__variant_tag__,
        )
        result = core_schema.definitions_schema(
            schema=core_schema.definition_reference_schema(schema_ref),
            definitions=[
                core_schema.json_or_python_schema(
                    json_schema=json_schema,
                    python_schema=core_schema.union_schema([json_schema, core_schema.any_schema()]),
                    serialization=core_schema.wrap_serializer_function_ser_schema(
                        kls.__pydantic_serialization__,
                        schema=core_schema.any_schema(),
                    ),
                    ref=schema_ref,
                )
            ]
        )

        return result

    def __python_value_restore__(
            self,
            kls: type["EnumetypedPydantic[typing.Any]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        if kls.__is_variant__:
            return kls(input_value)

        return super().__python_value_restore__(kls, input_value, info)

    def parse(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
    ) -> typing.Any:
        if isinstance(input_value, str):
            input_value = {input_value: None}

        type_key: str = input_value.pop(self.__variant_tag__) # noqa
        attr = kls.__names_deserialization__.get(type_key, type_key)

        return attr, input_value

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
            result.update(**value.__pydantic_serialization__(value, serializer))
        else:
            result.update(**serializer(value))

        return result
