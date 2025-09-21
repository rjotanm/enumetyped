from enumetyped.core import Enumetyped, Content, Empty

__all__ = [
    "Empty",
    "Enumetyped",
    "TypEnum", # deprecated
    "TypEnumContent", # deprecated
    "Content",
]

__package_name__ = "enumetyped"
__version__ = "0.4.1"
__description__ = "Type-containing enumeration"


TypEnum = Enumetyped
TypEnumContent = Content
NoValue = Empty
