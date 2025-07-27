from typing import Sequence

from toad._loop import loop_last

type Settings = dict[str, object]

SCHEMA = {
    "will": {"type": "str", "default": "Cool"},
    "user": {
        "help": "User information",
        "type": "object",
        "contents": {
            "name": {
                "help": "Your name",
                "type": "str",
                "default": "",
            },
            "email": {
                "help": "Your email",
                "type": "str",
                "validate": [{"type": "is_email"}],
                "default": "",
            },
        },
    },
    "accounts": {
        "help": "User accounts",
        "type": "data",
        "defaults": ["anthropic", "openai"],
        "contents": {
            "key": {
                "type": "str",
                "name": "key",
                "default": "",
            }
        },
    },
}


class InvalidKey(Exception):
    """The key is not in the schema."""


def parse_key(key: str) -> Sequence[str]:
    return key.split(".")


class Schema:
    def __init__(self, schema: Settings) -> None:
        self.schema = schema

    def set_value(self, settings: Settings, key: str, value: object) -> None:
        schema = self.schema
        keys = parse_key(key)
        for last, key in loop_last(keys):
            if last:
                settings[key] = value
            if key not in schema:
                raise InvalidKey()
            schema = schema[key]
            assert isinstance(schema, dict)
            if key not in settings:
                settings = settings[key] = {}

    def build_default(self) -> Settings:
        settings: Settings = {}

        def set_defaults(schema: Settings, settings: Settings) -> None:
            for key, sub_schema in schema.items():
                assert isinstance(sub_schema, dict)
                type = sub_schema["type"]
                if type == "str":
                    if (default := sub_schema.get("default")) is not None:
                        settings[key] = default

                elif type == "object":
                    if contents := sub_schema.get("contents"):
                        sub_settings = settings[key] = {}
                        set_defaults(contents, sub_settings)

                elif type == "data":
                    data_settings = settings[key] = {}
                    if defaults := sub_schema.get("defaults"):
                        for default in defaults:
                            sub_settings = data_settings[default] = {}
                            if data_schema := sub_schema.get("contents"):
                                set_defaults(data_schema, sub_settings)

        set_defaults(self.schema, settings)

        return settings


if __name__ == "__main__":
    from rich import print
    from rich.traceback import install

    # install(show_locals=True)

    # print(SCHEMA)
    schema = Schema(SCHEMA)
    settings = schema.build_default()
    print(settings)
