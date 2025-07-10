# Limitations

#### 0. Python haven`t inline TypedDict annotations

When we see on Rust\TypeScript type system, we can declare object with typed properties inplace:

```typescript
import { unionize, ofType } from "unionize";

const MyEnum = unionioze({
    Obj: ofType<{a: number; b: string}>(),
})
```

```rust
enum MyEnum {
    Obj {a: i32, b: String}
}
```

but python haven\`t this feature (mypy has experimental flag to support that), we must create TypedDict (or dataclass, or pydantic model, \`coz all of these types represent object)

```python
from typing_extensions import TypedDict
from enumetyped import Enumetyped, Content


class ObjDict(TypedDict):
    a: int
    b: str


class MyEnum(Enumetyped[Content]):
    Obj: type['MyEnum[ObjDict]']
```

#### 1. TypeScript can`t have empty variant

In Rust, we can create enum variant that does not contain a value 
```rust
enum MyEnum {
    Empty
}
```

In Python same, with special annotation

```python
from enumetyped import Enumetyped, Content, NoValue


class MyEnum(Enumetyped[Content]):
    Empty: type['MyEnum[NoValue]']


class FinEnum(Enumetyped[NoValue]):
    Empty: type['MyEnum']
```

TypeScript don\`t have same special type (so as extension).
As a solution, should use variant that contain empty object, something like this

```typescript
import { unionize, ofType } from "unionize";

const MyEnum = unionioze({
    Empty: ofType<{}>(),
})
```

```rust
enum MyEnum {
    Empty {}
}
```

```python
from typing_extensions import TypedDict
from enumetyped import Enumetyped, Content


class EmptyObj(TypedDict):
    pass


class MyEnum(Enumetyped[Content]):
    Empty: type['MyEnum[EmptyObj]']
```

#### 2. TypeScript can`t renaming\aliasing variants

Serde\Pydantic can rename field (or aliasing these) and handle it when value restored (deserializing), \`coz Serde and Pydantic - serialization libraries.
So unionize isn`t serialization library, it is only sugar over interfaces.
This sugar create constructor, which create object with needed representation.

Therefore, when we create API with these libraries, tags in unionized enum must have names, which stored in serialized structure.

#### 3. TypeScript can`t have self-referencing

In Rust\Python, we can create enum variant that contain self type 
```rust
enum MyEnum {
    Int(i32),
    SelfRef(Box<MyEnum>),
}
```

```python
from typing import Any
from enumetyped import Enumetyped, Content


class MyEnum(Enumetyped[Content]):
    Int: type['MyEnum[int]']
    SelfRef: type['MyEnum[MyEnum[Any]]']
```

But TypeScript can`t reproduce this behavior.
To get around this limitation, we must create second object.


```typescript
import { unionize, ofType } from "unionize";

interface EnumContaining {
    c: MyEnum
}

const MyEnum = unionioze({
    Ref: ofType<EnumContaining>(),
})
```

```rust
enum MyEnum {
    Int(i32),
    Ref {c: Box<MyEnum>},
}
```

```python
from typing_extensions import TypedDict
from enumetyped import Enumetyped, Content


class EnumContaining(TypedDict):
    c: 'MyEnum'


class MyEnum(Enumetyped[Content]):
    Int: type['MyEnum[int]']
    Ref: type['MyEnum[EnumContaining]']
```

#### 4. Internally representation should use for objects only

```python
from enumetyped import Enumetyped, Content


class MyEnum(Enumetyped[Content], key="key"):
    Int: type['MyEnum[int]']  # bad, error on runtime, but pass type check
```

```python
from typing_extensions import TypedDict
from enumetyped import Enumetyped, Content


class IntDict(TypedDict):
    val: int


class MyEnum(Enumetyped[Content], key="key"):
    Int: type['MyEnum[IntDict]']  # good, ambiguous, use other representation when possible
```