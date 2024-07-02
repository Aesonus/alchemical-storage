from typing import Any


def dict_to_params(
    test_cases: dict[str, Any],
):
    args = {
        "argvalues": [],
        "ids": [],
    }
    for key, value in test_cases.items():
        args["argvalues"].append(value)
        args["ids"].append(key)
    return args
