import argparse
from dataclasses import dataclass
from typing import Optional, Any


def str_to_bool(value: str) -> bool:
    """
    Convert string to boolean.

    Accepts: true, false (case-insensitive)
    """
    if isinstance(value, bool):
        return value
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    else:
        raise ValueError(f"Invalid value '{value}'. Please enter 'true' or 'false'")


@dataclass
class SmartArgItem:
    """
    Configuration for an argument in the SmartArgParser.

    :param flags: List of command-line flags for the argument.
    :param prompt: A prompt message for the argument.
    :param type: The expected type of the argument (e.g., str, int, float).
    :param default: Default value if the argument is not provided.
    """

    flags: list[
        str
    ]  # flags are the command line flags for the argument, e.g. ["--input", "-i"]
    prompt: str  # prompt is used for the help message
    arg_type: type = (
        str  # type is the expected type of the argument, e.g. str, int, float
    )
    default: Any = None  # default is the default value if the argument is not provided
    choices: Optional[list] = (
        None  # choices are the allowed values for the argument, if applicable
    )
    required: bool = True  # required indicates if the argument is mandatory or not
    action: Optional[str] = (
        None  # action is the action to be taken when the argument is provided, e.g. "store", "store_true", "store_false"
    )


class SmartArgParser:
    def __init__(
        self,
        schema: dict[str, SmartArgItem],
        description: str = "Smart Argument Parser",
    ):
        """
        Initialize the SmartArgParser with a schema and description.

        :param schema: A dictionary defining the expected arguments and their types.
        :param description: A description of the parser's purpose.
        """
        self.schema = schema  # This is a dict
        self.parser = argparse.ArgumentParser(description=description)
        self._define_arguments()  # Automatically define arguments based on the schema

    def _define_arguments(self):
        """
        Define the arguments based on the schema.
        """

        for name, config in self.schema.items():
            kwargs = {
                "help": config.prompt,
                "default": argparse.SUPPRESS,  # so that if the argument is not provided, it will not be included in the args
            }
            if config.action:
                kwargs["action"] = config.action
            else:
                # Use str_to_bool for boolean types to handle "True"/"False" strings
                kwargs["type"] = (
                    str_to_bool if config.arg_type is bool else config.arg_type
                )
                if config.choices:
                    kwargs["choices"] = config.choices

            self.parser.add_argument(*config.flags, dest=name, **kwargs)

    def _prompt(self, name: str, cfg: SmartArgItem) -> Any:
        """Interactively ask until we get a value (or return default/None)."""
        while True:
            suffix = f" [default: {cfg.default}]" if cfg.default is not None else ""
            raw = input(f"{cfg.prompt}{suffix}: ").strip()

            # 1) empty → default or None or repeat
            if not raw:
                if cfg.default is not None:
                    return cfg.default
                if not cfg.required:
                    return None
                print(f"⚠️  {name} is required.")
                continue

            # 2) enforce choices
            if cfg.choices and raw not in cfg.choices:
                print(f"⚠️  Invalid choice: {raw}.  Must be one of {cfg.choices}.")
                continue

            # 3) convert type
            try:
                # Use str_to_bool for boolean types
                converter = str_to_bool if cfg.arg_type is bool else cfg.arg_type
                return converter(raw)
            except Exception as e:
                print(f"⚠️  Could not convert '{raw}': {e}")

    def parse(self) -> dict[str, Any]:
        ns = self.parser.parse_args()
        result: dict[str, Any] = {}

        for name, cfg in self.schema.items():
            if hasattr(ns, name):
                # user supplied via CLI (or action default like store_true)
                result[name] = getattr(ns, name)
            else:
                if cfg.action == "store_true":
                    # For store_true flags, absence means False
                    result[name] = False
                else:
                    # user did NOT supply it → prompt interactively
                    result[name] = self._prompt(name, cfg)

        return result
