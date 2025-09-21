import typing
from pprint import pprint

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema, SchemaValidator
from pydantic_core.core_schema import SerializerFunctionWrapHandler

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
    __ext_tagged_schema_validator__: SchemaValidator

    def __init__(self, variant: str):
        self.__variant_tag__ = variant

    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from enumetyped.pydantic.core import EnumetypedPydantic

        schema_ref = f"{kls.__module__}.{kls.__name__}:{id(kls)}"

        json_schemas: dict[str, core_schema.CoreSchema] = {}
        real_schema_attrs = {}
        real_schemas: list[core_schema.CoreSchema] = []

        for attr in kls.__variants__.values():
            enum_variant: type[EnumetypedPydantic[Content]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)
            variant_schema = core_schema.typed_dict_field(core_schema.str_schema(pattern=attr))

            schema = {
                self.__variant_tag__: variant_schema,
            }
            if enum_variant.__content_type__ is Empty:
                real_schemas.append(core_schema.str_schema(pattern=attr))
            else:
                item_schema = handler.generate_schema(enum_variant.__content_type__)
                resolved = handler.resolve_ref_schema(item_schema)

                real_schema_attrs[attr] = core_schema.typed_dict_field(resolved, required=False)
                real_schemas.append(resolved)

                match resolved:
                    case {"type": "dataclass", "schema": {"fields": fields}}:
                        fields = {
                            field["name"]: {
                                "type": "typed-dict-field",
                                "schema": field["schema"]
                            } for field in fields
                        }
                        schema.update(**fields)
                    case {"type": "model", "schema": {"fields": fields}}:
                        fields = {
                            k: {
                                "type": "typed-dict-field",
                                "schema": v["schema"]
                            } for k, v in fields.items()
                        }
                        schema.update(**fields)
                    case {"type": "typed-dict", "fields": fields}:
                        schema.update(**fields)
                    case _:
                        raise TypeError(
                            f"Type of content must be a TypedDict, dataclass or BaseModel subclass, cause by {enum_variant.__content_type__} in {kls}"
                        )

            json_schemas[attr] = core_schema.typed_dict_schema(schema)

        # Store nested schema for deserializing
        self.__ext_tagged_schema_validator__ = SchemaValidator(core_schema.union_schema([
            core_schema.typed_dict_schema(real_schema_attrs),
            *real_schemas,
        ]))

        json_schema = core_schema.tagged_union_schema(
            choices=json_schemas,
            discriminator=self.__variant_tag__,
        )
        result = core_schema.definitions_schema(
            schema=core_schema.definition_reference_schema(schema_ref),
            definitions=[
                core_schema.json_or_python_schema(
                    json_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        json_schema,
                    ),
                    python_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        core_schema.union_schema([json_schema, core_schema.any_schema()])
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
        if isinstance(input_value, str):
            input_value = {input_value: None}

        type_key: str = input_value.pop(self.__variant_tag__) # noqa
        attr = kls.__names_deserialization__.get(type_key, type_key)

        if input_value:
            value = self.__ext_tagged_schema_validator__.validate_python({type_key: input_value})
            return attr, value[type_key]
        else:
            return attr, None

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
