import typing
from abc import ABC, abstractmethod

import pydantic as pydantic_
from pydantic_core import CoreSchema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

if typing.TYPE_CHECKING:
    from enumetyped.core import Content
    from enumetyped.pydantic.core import EnumetypedPydantic

__all__ = [
    "TaggedSerialization",
]


class TaggedSerialization(ABC):
    @abstractmethod
    def __get_pydantic_core_schema__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        raise NotImplementedError

    @abstractmethod
    def __python_value_restore__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        raise NotImplementedError

    @abstractmethod
    def __pydantic_serialization__(
            self,
            kls: type["EnumetypedPydantic[Content]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        raise NotImplementedError
