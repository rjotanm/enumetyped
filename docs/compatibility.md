# Compatibility

#### Rust Serde

[Serde documentation](https://serde.rs/enum-representations.html) have Externally\Internally\Adjacently tagged enum representation.

```rust
extern crate serde_json;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
enum OtherEnum {
    Int(i64),
}

#[derive(Serialize, Deserialize)]
struct AI32 {
    a: i32,
}

#[derive(Serialize, Deserialize)]
struct BStr {
    b: String,
}

// #[serde(tag = "key", content = "value")] <- adjacently
// #[serde(tag = "key")] <- internally
// without option (now) <- externally, default
#[derive(Serialize, Deserialize)]
enum MyEnum<'a> {
    Int(i32),
    Str(String),
    Other(OtherEnum),
    #[serde(rename = "Self", borrow)]
    Self_(Box<MyEnum<'a>>),
    NoValue,
    Optional(Option<bool>),
    List(Vec<String>),
    Dict(HashMap<String, String>),
    TypedDict { tm: BStr },
    DataClass(AI32),
    Model(BStr),
    #[serde(rename = "just_str_tuple", borrow)]
    StringTuple((&'a str, &'a str)),
}

#[derive(Serialize, Deserialize)]
struct FinModel<'a> {
    #[serde(rename = "enum", borrow)]
    enum_: MyEnum<'a>,
}

fn main() {
    // externally -> {"enum":{"Int":1}}
    // adjacently -> {"enum":{"key":"Int","value":1}}
    // internally -> not supported
    // python: MyEnum.Int(1)
    dump(MyEnum::Int(1));

    // externally -> {"enum":{"Str":"str"}}
    // adjacently -> {"enum":{"key":"Str","value":"str"}}
    // internally -> not supported
    // python: MyEnum.Str("str")
    dump(MyEnum::Str("str".to_string()));

    // externally -> {"enum":{"List":["list"]}}
    // adjacently -> {"enum":{"key":"List","value":["list"]}}
    // internally -> not supported
    // python: MyEnum.List(["list"])
    dump(MyEnum::List(vec!["list".to_string()]));

    // externally -> {"enum":{"just_str_tuple":["str","str2"]}}
    // adjacently -> {"enum":{"key":"just_str_tuple","value":["str","str2"]}}
    // internally -> not supported
    // python: MyEnum.StringTuple(("str", "str2"))
    dump(MyEnum::StringTuple(("str", "str2")));

    // externally -> {"enum":{"Self":{"Int":1}}}
    // adjacently -> {"enum":{"key":"Self","value":{"key":"Int","value":1}}}
    // internally -> not supported
    // python: MyEnum.Self(MyEnum.Int(1))
    dump(MyEnum::Self_(Box::new(MyEnum::Int(1))));

    // externally -> {"enum":{"DataClass":{"a":1}}}
    // adjacently -> {"enum":{"key":"DataClass","value":{"a":1}}}
    // internally -> {"enum":{"key":"DataClass","a":1}}}
    // python: MyEnum.DataClass(TestDataClass(a=1))
    dump(MyEnum::DataClass(AI32 { a: 1 }));

    // externally -> {"enum":{"Model":{"b":"test_model"}}}
    // adjacently -> {"enum":{"key":"Model","value":{"b":"test_model"}}}
    // internally -> {"enum":{"key":"Model", "b":"test_model"}}
    // python: MyEnum.Model(TestModel(b="test_model"))
    dump(MyEnum::Model(BStr { b: "test_model".to_string() }));

    // externally -> {"enum":{"TypedDict":{"tm":{"b":"test_model"}}}}
    // adjacently -> {"enum":{"key":"TypedDict","value":{"tm":{"b":"test_model"}}}}
    // internally -> {"enum":{"key":"TypedDict","tm":{"b":"test_model"}}}
    // python: MyEnum.TypedDict(TestTypedDict(tm=TestModel(b="test_model")))
    // python doesn`t have inline TypedDict now
    dump(MyEnum::TypedDict { tm: BStr { b: "test_model".to_string() } });

    // externally -> {"enum":{"Dict":{"a":"1","b":"2"}}}
    // adjacently -> {"enum":{"key":"Dict","value":{"a":"1","b":"2"}}}
    // internally -> {"enum":{"a":"1","b":"2","key":"Dict"}}
    // python: MyEnum.Dict({"a": "1", "b": "2"})
    dump(MyEnum::Dict(HashMap::from([("a".to_string(), "1".to_string()), ("b".to_string(), "2".to_string())])));

    // externally -> {"enum":"NoValue"}
    // adjacently -> {"enum":{"key":"NoValue"}}
    // internally -> {"enum":{"key":"NoValue"}}
    // python: MyEnum.NoValue()
    dump(MyEnum::NoValue);

    // externally -> {"enum":{"Optional":null}}
    // adjacently -> {"enum":{"key":"Optional","value":null}}
    // internally -> not supported
    // python: MyEnum.Optional(None)
    dump(MyEnum::Optional(None));
}
```

#### Typescript

TypeScript has library [unionize](https://github.com/pelotom/unionize) than provide Internally\Adjacently tagged representation.

For compatibility with this library was written extension over unionize: [extUnionize](https://github.com/rjotanm/ext-unionize) than provide Externally tagged representation.

```typescript
import { unionize, ofType } from "unionize";
import { extUnionize } from "ext-unionize";


interface AI32 {
    a: number
}

interface BStr {
    b: string
}

// const MyEnum = unionize({
//     ...
// }, {value: "value", tag: "key"}); <- adjacently

// const MyEnum = unionize({
//     ...
// }, {tag: "key"}); <- internally, default with {tag: "tag"} 

// const MyEnum = extUnionize({  <- externally
//     ...
// });


const OtherEnum = unionize({
    Int: ofType<number>(),
}, {value: "value", tag: "key"})

const MyEnum = unionize({
    Int: ofType<number>(),
    Str: ofType<string>(),
    Other: ofType<typeof OtherEnum>(),
    // Self: ofType<typeof MyEnum>(),  // TypeScript interfaces not support self referencing
    NoValue: ofType<null>(), // NoValue: ofType<{}>() - not compatible, `coz represent as Optional
    Optional: ofType<boolean | null>(),
    List: ofType<string[]>(),
    Dict: ofType<Record<string, string>>(),
    TypedDict: ofType<{ tm: BStr }>(),
    DataClass: ofType<AI32>(),
    Model: ofType<BStr>(),
    just_str_tuple: ofType<[string, string]>(), // TypeScript interfaces ofc not support renaming and aliasing
}, {value: "value", tag: "key"});

type MyEnum = typeof MyEnum._Union;


interface FinModel {
    enum: MyEnum;
}

function dump_and_load(en: MyEnum) {
    let model: FinModel = {
        enum: en,
    }
    let json = JSON.stringify(model)
    console.log(json)

    let result = JSON.parse(json) as FinModel
}

// externally -> {"enum":{"Int":1}}
// adjacently -> {"enum":{"key":"Int","value":1}}
// internally -> not supported
// python: MyEnum.Int(1)
dump_and_load(MyEnum.Int(1))

// externally -> {"enum":{"Str":"str"}}
// adjacently -> {"enum":{"key":"Str","value":"str"}}
// internally -> not supported
// python: MyEnum.Str("str")
dump_and_load(MyEnum.Str("str"))

// externally -> {"enum":{"List":["list"]}}
// adjacently -> {"enum":{"key":"List","value":["list"]}}
// internally -> not supported
// python: MyEnum.List(["list"])
dump_and_load(MyEnum.List(["list"]))

// externally -> {"enum":{"just_str_tuple":["str","str2"]}}
// adjacently -> {"enum":{"key":"just_str_tuple","value":["str","str2"]}}
// internally -> not supported
// python: MyEnum.StringTuple(("str", "str2"))
dump_and_load(MyEnum.just_str_tuple(["str", "str2"]))

// dump_and_load(MyEnum.Self(MyEnum.Int(1))) - not supported

// externally -> {"enum":{"DataClass":{"a":1}}}
// adjacently -> {"enum":{"key":"DataClass","value":{"a":1}}}
// internally -> {"enum":{"a":1,"key":"DataClass"}}
// python: MyEnum.DataClass(TestDataClass(a=1))
dump_and_load(MyEnum.DataClass({a: 1} as AI32))

// externally -> {"enum":{"Model":{"b":"test_model"}}}
// adjacently -> {"enum":{"key":"Model","value":{"b":"test_model"}}}
// internally -> {"enum":{"b":"test_model","key":"Model"}}
// python: MyEnum.Model(TestModel(b="test_model"))
dump_and_load(MyEnum.Model({b: "test_model"} as BStr))

// externally -> {"enum":{"TypedDict":{"tm":{"b":"test_model"}}}}
// adjacently -> {"enum":{"key":"TypedDict","value":{"tm":{"b":"test_model"}}}}
// internally -> {"enum":{"tm":{"b":"test_model"},"key":"TypedDict"}}
// python: MyEnum.TypedDict(TestTypedDict(tm=TestModel(b="test_model")))
// python doesn`t have inline TypedDict now
dump_and_load(MyEnum.TypedDict({tm: {b: "test_model"} as BStr}))

// externally -> {"enum":{"Dict":{"a":"1","b":"2"}}}
// adjacently -> {"enum":{"key":"Dict","value":{"a":"1","b":"2"}}}
// internally -> {"enum":{"a":"1","b":"2","key":"Dict"}}
// python: MyEnum.Dict({"a": "1", "b": "2"})
dump_and_load(MyEnum.Dict({a: "1", b: "2"}))

// dump_and_load(MyEnum.NoValue(null)) - not supported

// externally -> {"enum":{"Optional":null}}
// adjacently -> {"enum":{"key":"Optional","value":null}}
// internally -> not supported
// python: MyEnum.Optional(None)
dump_and_load(MyEnum.Optional(null))
```

#### Other

- [Limitations](limitations.md)
