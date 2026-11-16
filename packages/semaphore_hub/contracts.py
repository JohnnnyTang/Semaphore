"""Installed-package schema access; references resolve locally, never over HTTP."""

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS = ("durable-http.schema.json", "http.schema.json", "events.schema.json")


def load(name: str) -> dict:
    if name not in (*SCHEMAS, "durable-openapi.json"):
        raise ValueError("unknown hub contract")
    return json.loads(files("semaphore_hub").joinpath("data", name).read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def validator(
    definition: str | None = None, document: str = "durable-http.schema.json"
) -> Draft202012Validator:
    if document not in SCHEMAS:
        raise ValueError("unknown schema")
    documents = [load(name) for name in SCHEMAS]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in documents
    )
    schema = documents[SCHEMAS.index(document)]
    if definition is None:
        return Draft202012Validator(schema, registry=registry)
    if definition not in schema.get("$defs", {}):
        raise ValueError("unknown definition")
    reference = {"$ref": schema["$id"] + "#/$defs/" + definition}
    return Draft202012Validator(reference, registry=registry)
