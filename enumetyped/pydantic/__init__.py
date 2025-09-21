import pydantic

if tuple(map(int, pydantic.version.VERSION.split('.'))) < (2, 9, 0):
    raise ValueError("Pydantic version must be >=2.9.0")


from .core import (
    Rename,
    EnumetypedPydantic,
    FieldMetadata,
)

TypEnumPydantic = EnumetypedPydantic

__all__ = [
    "FieldMetadata",
    "Rename",
    "EnumetypedPydantic",
    "TypEnumPydantic",
]
