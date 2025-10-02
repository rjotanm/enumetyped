import inspect
import typing
from contextvars import ContextVar

import pydantic as pydantic_
from pydantic_core import CoreSchema, core_schema, SchemaValidator
from pydantic_core.core_schema import SerializerFunctionWrapHandler

from enumetyped.core import Content, Empty
from enumetyped.pydantic.serialization.tagging import Tagging

if typing.TYPE_CHECKING:
    from enumetyped.core import Content
    from enumetyped.pydantic.core import EnumetypedPydantic

__all__ = [
    "ExternalTagging",
    "AlwaysSerializeToDict",
]


AlwaysSerializeToDict: ContextVar[bool] = ContextVar("AlwaysSerializeToDict", default=False)


class ExternalTagging(Tagging):
    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        from enumetyped.pydantic.core import EnumetypedPydantic

        schema_ref = f"{kls.__module__}.{kls.__name__}:{id(kls)}"

        json_schema_attrs = {}
        schemas = []

        for attr in kls.__variants__.values():
            enum_variant: type[EnumetypedPydantic[Content]] = getattr(kls, attr)
            attr = kls.__names_serialization__.get(attr, attr)

            is_enumetyped_variant = (
                    inspect.isclass(enum_variant.__content_type__) and
                    issubclass(enum_variant.__content_type__, EnumetypedPydantic)
            )

            item_schema: core_schema.CoreSchema

            if is_enumetyped_variant:
                kls_: type = enum_variant.__content_type__  # type: ignore
                child_schema_ref = f"{kls_.__module__}.{kls_.__name__}:{id(kls_)}"
                if child_schema_ref == schema_ref:
                    item_schema = core_schema.definition_reference_schema(schema_ref)
                else:
                    item_schema = handler.generate_schema(enum_variant.__content_type__)
            elif enum_variant.__content_type__ is Empty:
                schemas.append(core_schema.str_schema(pattern=attr))
                item_schema = core_schema.none_schema()
            else:
                item_schema = handler.generate_schema(enum_variant.__content_type__)

            json_schema_attrs[attr] = core_schema.typed_dict_field(item_schema, required=False)

        schemas.append(core_schema.typed_dict_schema(json_schema_attrs))  # type: ignore  # noqa

        result = core_schema.definitions_schema(
            schema=core_schema.definition_reference_schema(schema_ref),
            definitions=[
                core_schema.json_or_python_schema(
                    json_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        core_schema.union_schema(schemas),  # type: ignore  # noqa
                    ),
                    python_schema=core_schema.with_info_after_validator_function(
                        kls.__python_value_restore__,
                        core_schema.union_schema([core_schema.union_schema(schemas), core_schema.any_schema()]),  # type: ignore  # noqa
                    ),
                    serialization=core_schema.wrap_serializer_function_ser_schema(
                        kls.__pydantic_serialization__
                    ),
                    ref=schema_ref
                )
            ],
        )

        self.core_schema = result
        return result

    def parse(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
    ) -> typing.Any:
        if isinstance(input_value, str):
            input_value = {input_value: None}

        for attr, value in input_value.items():  # noqa
            attr = kls.__names_deserialization__.get(attr, attr)
            return attr, value

    def __pydantic_serialization__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        from enumetyped.pydantic.core import EnumetypedPydantic

        attr = model.__variant_name__
        attr = model.__names_serialization__.get(attr, attr)

        value = model._value  # noqa

        if model.__content_type__ is Empty and not AlwaysSerializeToDict.get():
            return attr
        elif isinstance(value, EnumetypedPydantic):
            content = model.value.__pydantic_serialization__(value, serializer)
        else:
            content = serializer(value)

        return {attr: content}
