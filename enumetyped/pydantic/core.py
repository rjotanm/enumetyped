import importlib
import inspect
import types
import typing
from dataclasses import dataclass
from pprint import pprint

import pydantic
import pydantic as pydantic_
import typing_extensions
from annotated_types import GroupedMetadata, BaseMetadata
from pydantic import TypeAdapter
from pydantic.json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaMode
from pydantic.main import IncEx  # noqa
from pydantic_core import core_schema, SchemaValidator
from pydantic_core.core_schema import ValidationInfo, SerializerFunctionWrapHandler

from enumetyped.core import EnumetypedMeta, Content, Enumetyped

__all__ = [
    "Rename",
    "FieldMetadata",
    "EnumetypedPydantic",
    "EnumetypedPydanticMeta",
    "eval_content_type",
]

from enumetyped.pydantic.serialization import AdjacentTagging, InternalTagging, ExternalTagging
from enumetyped.pydantic.serialization.tagging import Tagging


@dataclass(frozen=True, slots=True)
class Rename(BaseMetadata):
    value: str


@dataclass
class FieldMetadata(GroupedMetadata):
    rename: typing.Optional[str] = None

    def __iter__(self) -> typing.Iterator[BaseMetadata]:
        if self.rename is not None:
            yield Rename(self.rename)


def eval_content_type(cls: type['EnumetypedPydantic[Content]']) -> type:
    # Eval annotation into real object
    base = cls.__orig_bases__[0]  # type: ignore
    module = importlib.import_module(base.__module__)
    return eval(cls.__content_type__, module.__dict__)  # type: ignore


class EnumetypedPydanticMeta(EnumetypedMeta):
    __tagging__: Tagging

    def __new__(
            cls,
            cls_name: str,
            bases: tuple[typing.Any],
            class_dict: dict[str, typing.Any],
            variant: typing.Optional[str] = None,
            content: typing.Optional[str] = None,
    ) -> typing.Any:
        enum_class = super().__new__(cls, cls_name, bases, class_dict)
        if enum_class.__annotations__.get("__abstract__"):
            return enum_class

        if enum_class.__is_variant__:
            return enum_class

        enum_class.__names_serialization__ = dict()
        enum_class.__names_deserialization__ = dict()

        if variant is not None and content is not None:
            enum_class.__tagging__ = AdjacentTagging(variant, content)
        elif variant is not None:
            enum_class.__tagging__ = InternalTagging(variant)
        else:
            enum_class.__tagging__ = ExternalTagging()

        annotation: typing.Union[type[typing_extensions.Annotated[typing.Any, BaseMetadata]], type]
        for attr, annotation in enum_class.__annotations__.items():
            if not hasattr(annotation, "__args__"):
                continue

            enum_variant = getattr(enum_class, attr)
            if isinstance(enum_variant.__content_type__, str):
                try:
                    enum_variant.__content_type__ = eval_content_type(enum_variant)
                except NameError:
                    ...

            if isinstance(annotation, typing._AnnotatedAlias):  # type: ignore  # noqa
                metadata: list[typing.Union[BaseMetadata, GroupedMetadata]] = []
                for v in annotation.__metadata__:
                    if isinstance(v, FieldMetadata):
                        metadata.extend(v)
                    else:
                        metadata.append(v)

                for __meta__ in metadata:
                    if isinstance(__meta__, Rename):
                        if __meta__.value in enum_class.__names_deserialization__:
                            raise ValueError(f"{cls_name}: Two or many field renamed to `{__meta__.value}`")

                        enum_class.__names_serialization__[attr] = __meta__.value
                        enum_class.__names_deserialization__[__meta__.value] = attr

        if not enum_class.__is_variant__:
            module = importlib.import_module(enum_class.__module__)
            module.__dict__[enum_class.__name__] = enum_class
            for k, v in enum_class.__annotations__.items():
                variant_cls: type[EnumetypedPydantic[typing.Any]] = getattr(enum_class, k)
                variant_cls.__module__ = enum_class.__module__
                try:
                    not_eval_ct = variant_cls.__content_type__
                    content_type = variant_cls.content_type()
                    if type(content_type) is types.GenericAlias:  # type: ignore  # noqa
                        # Force generic variants like `Var` below
                        # to RootModel like `VarRoot`
                        #
                        #   class Container(pydantic.RootModel):
                        #       root: list['A']
                        #
                        #
                        #   class A(EnumetypedPydantic[Content]):
                        #       Var: type["A[list[A]]"]
                        #       VarRoot: type["A[]"]
                        #

                        variant_cls.__content_type__ = pydantic.RootModel[not_eval_ct]  # type: ignore  # noqa
                        variant_cls.__content_type__.model_rebuild(_types_namespace=module.__dict__)  # noqa
                        variant_cls.__implicit_root_model__ = True
                    try:
                        annotation = enum_class.__annotations__[k]
                        if isinstance(annotation, typing._AnnotatedAlias):  # type: ignore  # noqa
                            # Save annotations like
                            #
                            #   class A(EnumetypedPydantic[Content]):
                            #       Var: typing.Annotated[type["A[str]"], Rename("Vapppp")]
                            #
                            _, *annotations = typing_extensions.get_args(annotation)
                            annotation.__origin__ = type[enum_class[content_type]]
                        else:
                            enum_class.__annotations__[k] = type[enum_class[content_type]]
                    except TypeError:
                        # Fall on below case
                        #
                        # class SimpleEnum(EnumetypedPydantic[Empty]):
                        #     V1: type["SimpleEnum"]
                        #     V2: type["SimpleEnum"]
                        pass

                except NameError:
                    # May fall when Content name defined after Enumetyped definition
                    #
                    # class A(...)
                    #     Var: type['A[B]']
                    #
                    # class B:
                    #    ...
                    raise TypeError(
                        f"Defer defined models currently is not supported, cause by \
                        {enum_class.__annotations__[k]} in {enum_class}!"
                    )

        return enum_class


class EnumetypedPydantic(Enumetyped[Content], metaclass=EnumetypedPydanticMeta):
    """ Class for created rust-like enums

    Can be used for creating complex API data schemas with simple usage.
    ``` python
        import pydantic
        import json
        from enumetyped import Content, Empty
        from enumetyped.pydantic import EnumetypedPydantic

        class AdItem(pydantic.BaseModel):
            ...


        class RootContainer(pydantic.RootModel):
            root: list["ExampleFeed"]


        class ExampleFeed(EnumetypedPydantic[Content]):
            # variant with simple type
            Post: type["ExampleFeed[str]"]
            # variant with other pydantic or enumetyped model
            Ad: type["ExampleFeed[AdItem]"]

            # variant without value must have Content=Empty
            ClientGenericContainer: type["ExampleFeed[Empty]"]

            # forward self reference allowed, but it`s no practical use
            SelfRef: type["ExampleFeed[ExampleFeed]"]

            # self reference within generics in root models
            SelfList: type["ExampleFeed[RootContainer]"]

            # self reference within inplace generics
            # (RootModel used implicitly)
            SelfListForce: type["ExampleFeed[list[ExampleFeed]]"]


        # use adapter for serialization\\deserialization in complex types
        feed_adapter = pydantic.TypeAdapter(list[ExampleFeed])

        feed = [
            ExampleFeed.Post("test"),
            ExampleFeed.Ad(AdItem()),
            ExampleFeed.ClientGenericContainer(),
        ]
        serialized = feed_adapter.dump_json(feed)  # [{"Post":"test"},{"Ad":{}},"ClientGenericContainer"]
        deserialized = feed_adapter.validate_json(serialized)
        assert feed == deserialized

        # use in pydantic models as-is
        class TopLevelModel(pydantic.BaseModel):
            feed: ExampleFeed

        data = TopLevelModel(feed=ExampleFeed.Post("test"))
        serialized = data.model_dump_json()  # {"feed":{"Post":"test"}}
        deserialized = TopLevelModel.model_validate_json(serialized)
        assert data == deserialized

        # use pydantic-like methods
        ad = ExampleFeed.Ad(AdItem())
        serialized = ad.model_dump_json()  # {"Ad":{}}
        deserialized = ExampleFeed.model_validate_json(serialized)
        assert ad == deserialized

        # or use tagging-dependent constructor
        container = ExampleFeed.ClientGenericContainer()
        serialized = container.model_dump_json()  # "ClientGenericContainer" - External

        raw_deserialized = json.loads(serialized)
        deserialized = ExampleFeed(raw_deserialized)

        assert container == deserialized

        post = ExampleFeed.Post("test")
        serialized = post.model_dump_json()  # {"Post":"test"}

        raw_deserialized = json.loads(serialized)
        deserialized = ExampleFeed(raw_deserialized)
        deserialized_kwargs = ExampleFeed(**raw_deserialized)

        assert post == deserialized
        assert post == deserialized_kwargs

        # self containing
        self_containing = ExampleFeed.SelfRef(ExampleFeed.SelfRef(ExampleFeed.Post("test")))

        serialized = self_containing.model_dump_json()  # {"SelfRef":{"SelfRef":{"Post":"test"}}}

        deserialized = ExampleFeed.model_validate_json(serialized)
        assert self_containing == deserialized

        raw_deserialized = json.loads(serialized)
        deserialized = ExampleFeed(raw_deserialized)
        deserialized_kwargs = ExampleFeed(**raw_deserialized)

        assert self_containing == deserialized
        assert self_containing == deserialized_kwargs

        # self containing with generic container
        self_containing = ExampleFeed.SelfList(RootContainer(root=[ExampleFeed.SelfRef(ExampleFeed.Post("test"))]))

        serialized = self_containing.model_dump_json()  # {"SelfList":[{"SelfRef":{"Post":"test"}}]}

        raw_deserialized = json.loads(serialized)
        deserialized = ExampleFeed(raw_deserialized)
        deserialized_kwargs = ExampleFeed(**raw_deserialized)
        deserialized_forward = ExampleFeed.model_validate_json(serialized)

        assert self_containing == deserialized
        assert self_containing == deserialized_kwargs
        assert self_containing == deserialized_forward

        # self containing with generic container (implicitly create RootModel)
        self_containing = ExampleFeed.SelfListForce([ExampleFeed.SelfRef(ExampleFeed.Post("test"))])

        serialized = self_containing.model_dump_json()  # {"SelfListForce":[{"SelfRef":{"Post":"test"}}]}

        raw_deserialized = json.loads(serialized)
        deserialized = ExampleFeed(raw_deserialized)
        deserialized_kwargs = ExampleFeed(**raw_deserialized)
        deserialized_forward = ExampleFeed.model_validate_json(serialized)

        assert self_containing == deserialized
        assert self_containing == deserialized_kwargs
        assert self_containing == deserialized_forward
    ```


    """
    __abstract__: typing_extensions.Never

    __names_serialization__: typing.ClassVar[dict[str, str]]
    __names_deserialization__: typing.ClassVar[dict[str, str]]

    __tagging__: typing.ClassVar[Tagging]
    __implicit_root_model__: bool = False

    _type_adapter: typing.Optional[TypeAdapter[typing_extensions.Self]] = None

    def __new__(cls, *args, **kwargs):  # type: ignore  # noqa
        options = None
        if args:
            arg = args[0]
            if not cls.__is_variant__:
                options = arg
        else:
            options = kwargs

        if options:
            return cls.model_validate(options)
        return super().__new__(cls, *args, **kwargs)  # type: ignore  # noqa

    @property
    def value(self) -> typing.Optional[Content]:
        if self.__implicit_root_model__:
            return self._value.root  # type: ignore  # noqa
        return self._value

    @typing.overload
    def __init__(self):  # type: ignore
        pass

    @typing.overload
    def __init__(self, content: Content):
        pass

    @typing.overload
    def __init__(self, **kwargs):  # type: ignore  # noqa
        pass

    def __init__(self, *args, **kwargs):  # type: ignore  # noqa
        if self._value is not None:
            # Prevent parse data on second call
            return

        if args and self.__implicit_root_model__:
            value = args[0]
            if not isinstance(value, self.__content_type__):  # type: ignore  # noqa
                self._value = self.__content_type__(value)  # type: ignore  # noqa
            else:
                super().__init__(value)
        else:
            super().__init__(*args)

    @classmethod
    def content_type(cls) -> type:
        # Resolve types when __content_type__ declare after cls declaration
        if isinstance(cls.__content_type__, str):
            cls.__content_type__ = eval_content_type(cls)
        return cls.__content_type__

    @classmethod
    def __variant_constructor__(
            cls: type["EnumetypedPydantic[typing.Any]"],
            value: typing.Any,
            info: ValidationInfo,
    ) -> "EnumetypedPydantic[typing.Any]":
        if inspect.isclass(cls.content_type()) and issubclass(cls.content_type(), EnumetypedPydantic):
            value = cls.__python_value_restore__(value, info)

        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
            cls: type["EnumetypedPydantic[typing.Any]"],
            source_type: typing.Any,
            handler: pydantic_.GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return cls.__tagging__.__get_pydantic_core_schema__(
            cls,  # type: ignore
            source_type,
            handler,
        )

    @classmethod
    def __python_value_restore__(
            cls: type["EnumetypedPydantic[typing.Any]"],
            input_value: typing.Any,
            info: ValidationInfo,
    ) -> typing.Any:
        return cls.__tagging__.__python_value_restore__(
            cls,  # type: ignore
            input_value,
            info,
        )

    @classmethod
    def __pydantic_serialization__(
            cls: type["EnumetypedPydantic[typing.Any]"],
            model: typing.Any,
            serializer: SerializerFunctionWrapHandler,
    ) -> typing.Any:
        return cls.__tagging__.__pydantic_serialization__(
            cls,  # type: ignore
            model,
            serializer,
        )

    @classmethod
    def adapter(cls) -> TypeAdapter[typing_extensions.Self]:
        if cls._type_adapter is None:
            cls._type_adapter = TypeAdapter(cls)

        return cls._type_adapter

    def model_dump(
        self,
        *,
        mode: typing.Literal['json', 'python'] = 'python',
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: typing.Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | typing.Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
    ) -> dict[str, typing.Any]:
        return self.adapter().dump_python(  # type: ignore
            self,
            mode=mode,
            by_alias=by_alias,
            include=include,
            exclude=exclude,
            context=context,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: typing.Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | typing.Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False,
    ) -> str:
        return self.adapter().dump_json(
            self,
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        ).decode()

    @classmethod
    def json_schema(
        cls,
        *,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, typing.Any]:
        return cls.adapter().json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
        )

    @classmethod
    def model_validate(
        cls,
        obj: typing.Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_python(obj, strict=strict, from_attributes=from_attributes, context=context)

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_json(json_data, strict=strict, context=context)

    @classmethod
    def model_validate_strings(
        cls,
        obj: typing.Any,
        *,
        strict: bool | None = None,
        context: typing.Any | None = None,
    ) -> typing_extensions.Self:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        return cls.adapter().validate_strings(obj, strict=strict, context=context)

