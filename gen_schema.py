from re import findall
from json import dumps
from typing import Any

from types import GenericAlias
from typing import Any, ForwardRef
from jsonschema import Draft7Validator
from major.requirements import REQUIREMENTS_MAP

schema: dict[str, Any] = {
    "$schema": Draft7Validator.META_SCHEMA["$id"],
    "$comment": f"Generated by {__file__} on {__import__('datetime').datetime.now()}",
    "type": "object",
    "properties": {
        "abbreviation": {"type": "string"},
        "catalog_uri": {"type": "string"},
        "minimum_credit_hours": {"type": "number"},
        "name": {"type": "string"},
        "school": {"type": "string"},
        "subtype": {"type": "string"},
        "year": {"type": "string"},
        "requirements": {
            "type": "object",
            "properties": {
                "core": {"type": "string"},
                "major": {"type": "array", "items": {"$ref": "#/$defs/requirement"}},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

requirement_schemas: list[dict[str, Any]] = []

metadata_schema = {
    "type": "object",
    "properties": {"id": {"type": "string"}},
    "requirements": ["id"],
}


def primitive_to_schema(primitive: Any | None) -> dict[str, Any]:
    if primitive == int:
        return {"type": "integer"}
    elif primitive == str:
        return {"type": "string"}
    elif primitive == bool:
        return {"type": "boolean"}
    else:
        raise Exception("Unknown primitive", primitive)


def forward_ref_to_schema(ref: ForwardRef) -> dict[str, Any]:
    ref_type = ref._evaluate(globalns={}, localns={}, recursive_guard=frozenset())

    if isinstance(ref_type, GenericAlias):
        args = ref_type.__args__
        if ref_type.__qualname__ == "list":
            base: dict[str, Any] = {"type": "array"}
            list_type = args[0]
            try:
                base["items"] = primitive_to_schema(list_type)
            except Exception:
                if isinstance(list_type.__annotations__, dict):
                    for i in list_type.__annotations__:
                        base["items"] = forward_ref_to_schema(
                            list_type.__annotations__[i]
                        )
                else:
                    raise Exception("Unhandled list type", list_type)
            return base
        elif ref_type.__qualname__ == "dict":
            raise NotImplementedError("dict type not implemented")
            # base: dict[str, Any] = {"type": "object"}
            # # TODO: This
            # key_type = args[0]
            # value_type = args[1]
            # print(key_type, value_type)
            # return base
        else:
            raise Exception("Unknown generic alias", ref_type.__qualname__)
    elif isinstance(ref_type, type):
        return primitive_to_schema(ref_type)
    else:
        raise Exception("Expected type, got", type(ref_type), ref_type)


for req_name in REQUIREMENTS_MAP:
    req = REQUIREMENTS_MAP[req_name]
    requirement_schema_props: dict[str, Any] = {"matcher": {"const": req_name}}

    for prop_name in req.JSON.__annotations__:
        prop_type = req.JSON.__annotations__[prop_name]
        if isinstance(prop_type, ForwardRef):
            s = (
                forward_ref_to_schema(prop_type)
                if prop_name != "metadata"
                else metadata_schema
            )
            requirement_schema_props[prop_name] = s
        else:
            raise Exception("Expected property to be forward ref")
    requirement_schema_props.setdefault("metadata", metadata_schema)
    requirement_schemas.append(requirement_schema_props)

for i in requirement_schemas:
    if "requirements" in i:
        i["requirements"] = {"type": "array", "items": {"$ref": "#/$defs/requirement"}}
    if "prefix_groups" in i:
        i["prefix_groups"] = {"type": "array", "items": {"$ref": "#/$defs/requirement"}}

schema["$defs"] = {
    "requirement": {
        "anyOf": list(
            map(
                lambda x: {
                    "type": "object",
                    "properties": x,
                    "additionalProperties": False,
                    "requirements": ["metadata"],
                },
                requirement_schemas,
            )
        )
    },
}

print("Validating schema...")
Draft7Validator.check_schema(schema)

print("Writing schema...")

def requirement_schema_to_empty_json_body(s: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for prop_name in s:
        prop_type = s[prop_name]
        if prop_name == "metadata":
            body[prop_name] = {"id": "$UUID"}
        elif prop_name == "matcher":
            body[prop_name] = s["matcher"]["const"]
        elif prop_type["type"] == "array":
            body[prop_name] = []
        elif prop_type["type"] == "string":
            body[prop_name] = ""
        elif prop_type["type"] == "integer":
            body[prop_name] = 0
        elif prop_type["type"] == "boolean":
            body[prop_name] = False
        else:
            raise Exception("Unknown property type", prop_type)
    return body


snips = dict(
    zip(
        list(map(lambda curr: curr["matcher"]["const"], requirement_schemas)),  # type: ignore
        list(
            map(
                lambda curr: {
                    "prefix": ["".join(
                        findall("[A-Z]", curr["matcher"]["const"])
                    ).lower(), curr["matcher"]["const"]],
                    "description" : f'Empty body of {curr["matcher"]["const"]}',
                    "body": dumps(requirement_schema_to_empty_json_body(curr), indent=2)
                },
                requirement_schemas,
            )
        ),
    )
)

snips["$comment"] =  f"Generated by {__file__} on {__import__('datetime').datetime.now()}" # type: ignore

with open(".vscode/major.schema.json", "w") as f:
    f.write(dumps(schema, indent=2))
with open(".vscode/requirements.code-snippets", "w") as f:
    f.write(dumps(snips, indent=2))

print("Done!")
