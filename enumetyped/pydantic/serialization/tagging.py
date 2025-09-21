import typing
from abc import ABC, abstractmethod

import pydantic as pydantic_
from pydantic_core import CoreSchema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

if typing.TYPE_CHECKING:
    from enumetyped.core import Content
    from enumetyped.pydantic.core import EnumetypedPydantic

__all__ = [
    "Tagging",
]


class Tagging(ABC):
    @abstractmethod
    def parse(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
    ) -> typing.Any:
        raise NotImplementedError

    @abstractmethod
    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        raise NotImplementedError

    def __python_value_restore__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        from enumetyped.pydantic.core import EnumetypedPydantic
        if isinstance(input_value, EnumetypedPydantic) or isinstance(input_value, pydantic_.BaseModel):
            return input_value

        attr, value = self.parse(kls, input_value)
        return getattr(kls, attr).__variant_constructor__(value, info)

    @abstractmethod
    def __pydantic_serialization__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        raise NotImplementedError
