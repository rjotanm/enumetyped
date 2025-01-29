import typing
from abc import ABC, abstractmethod

import pydantic as pydantic_
from pydantic_core import CoreSchema
from pydantic_core.core_schema import SerializerFunctionWrapHandler, ValidationInfo

if typing.TYPE_CHECKING:
    from ...core import TypEnumContent  # type: ignore
    from ..core import TypEnumPydantic  # type: ignore

__all__ = [
    "TaggedSerialization",
]


class TaggedSerialization(ABC):
    @abstractmethod
    def __get_pydantic_core_schema__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            _source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> CoreSchema:
        raise NotImplementedError

    @abstractmethod
    def __python_value_restore__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        raise NotImplementedError

    @abstractmethod
    def __pydantic_serialization__(
            self,
            kls: type["TypEnumPydantic[TypEnumContent]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        raise NotImplementedError
