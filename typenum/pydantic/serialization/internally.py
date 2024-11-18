import typing

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema, SchemaValidator
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

from typenum.core import NoValue, TypEnumContent
from typenum.pydantic.serialization.tagged import TaggedSerialization

if typing.TYPE_CHECKING:
    from ..core import TypEnumPydantic  # type: ignore

__all__ = [
    "InternallyTagged",
]


class InternallyTagged(TaggedSerialization):
    __variant_tag__: str
    __ext_tagged_schema_validator__: SchemaValidator

    def __init__(self, variant: str):
        self.__variant_tag__ = variant

    def __get_pydantic_core_schema__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from typenum.pydantic.core import TypEnumPydantic

        json_schemas: dict[str, core_schema.CoreSchema] = {}
        real_schema_attrs = {}
        real_schemas: list[core_schema.CoreSchema] = []

        for attr in kls.__variants__.values():
            enum_variant: type[TypEnumPydantic[TypEnumContent]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)
            variant_schema = core_schema.typed_dict_field(core_schema.str_schema(pattern=attr))

            schema = {
                self.__variant_tag__: variant_schema,
            }
            if enum_variant.__content_type__ is NoValue:
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
                            "Type of content must be a TypedDict, dataclass or BaseModel subclass"
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
        return core_schema.json_or_python_schema(
            json_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                json_schema,
            ),
            python_schema=core_schema.with_info_after_validator_function(
                kls.__python_value_restore__,
                core_schema.any_schema(),
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
        if isinstance(input_value, kls):
            return input_value

        type_key = input_value.pop(self.__variant_tag__)
        attr = kls.__names_deserialization__.get(type_key, type_key)

        if input_value:
            value = self.__ext_tagged_schema_validator__.validate_python({type_key: input_value})
            return getattr(kls, attr).__variant_constructor__(value[type_key], info)
        else:
            return getattr(kls, attr).__variant_constructor__(None, info)

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
        elif isinstance(model.value, kls):
            result.update(**kls.__pydantic_serialization__(model.value, serializer))
        else:
            result.update(**serializer(model.value))

        return result
