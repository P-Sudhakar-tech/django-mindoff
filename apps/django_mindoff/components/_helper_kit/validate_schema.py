from typing import Any, Dict, List, Union, get_args, get_origin, Literal
from ..validation_kit import mo_validation_kit

MAX_NESTING_DEPTH = 20
MAX_LIST_VARIANTS = 1


# ------------------------
# Main Function
# ------------------------
def validate_schema(data: Any, schema: Any, depth: int = 0) -> None:
    """Iterative schema validator with depth and homogeneous list safeguards."""

    stack = [(data, schema, depth, "root")]

    while stack:
        value, sch, current_depth, path = stack.pop()
        mo_validation_kit.ensure_lesser_equal(
            current_depth,
            MAX_NESTING_DEPTH,
            msg=f"Payload nesting too deep at {path}",
            is_aggregate=True,
        )

        origin = get_origin(sch)
        args = get_args(sch)

        # ------------------------
        # Dispatch table for schema handling
        # ------------------------
        handler = _get_handler(sch, origin)
        handler(value, sch, origin, args, stack, current_depth, path)

    mo_validation_kit.finalize()


# ------------------------
# First-level Handlers (with inlined logic)
# ------------------------
def _get_handler(sch, origin):
    if isinstance(sch, type):
        return _handle_type
    if origin is Union:
        return _handle_union
    if origin is Literal:
        return _handle_literal
    if isinstance(sch, list):
        return _handle_list_shorthand
    if origin in (list, List):
        return _handle_list_typehint
    if origin in (dict, Dict):
        return _handle_dict_typehint
    if isinstance(sch, dict):
        return _handle_dict_shorthand
    raise TypeError(f"Unsupported schema: {sch}")


def _handle_type(value, sch, origin, args, stack, depth, path):
    mo_validation_kit.ensure_type(
        value,
        sch,
        msg=f"{path} must be {sch.__name__}, got {type(value).__name__}",
        is_aggregate=True,
    )


def _handle_union(value, sch, origin, args, stack, depth, path):
    if type(None) in args and value is None:
        return
    non_none_args = [a for a in args if a is not type(None)]
    __success = False
    for t in non_none_args:
        stack.append((value, t, depth, path))
        __success = True
        break
    mo_validation_kit.ensure_truthy(
        __success,
        msg=f"{path} must match one of {args}, got {type(value).__name__}",
        is_aggregate=True,
    )


def _handle_literal(value, sch, origin, args, stack, depth, path):
    mo_validation_kit.ensure_in(
        value,
        args,
        msg=f"{path} must be one of {args}, got {value}",
        is_aggregate=True,
    )


def _handle_list_shorthand(value, sch, origin, args, stack, depth, path):
    mo_validation_kit.ensure_equal(
        len(sch),
        MAX_LIST_VARIANTS,
        msg="List schema must have exactly one type",
        is_aggregate=True,
    )
    # Inlined _check_type
    mo_validation_kit.ensure_type(
        value, list, msg=f"{path} must be a list", is_aggregate=True
    )
    # Inlined _append_stack
    for i, item in enumerate(value):
        stack.append((item, sch[0], depth + 1, f"{path}[{i}]"))


def _handle_list_typehint(value, sch, origin, args, stack, depth, path):
    item_type = args[0] if args else Any
    mo_validation_kit.ensure_type(
        value, list, msg=f"{path} must be a list", is_aggregate=True
    )
    for i, item in enumerate(value):
        stack.append((item, item_type, depth + 1, f"{path}[{i}]"))


def _handle_dict_typehint(value, sch, origin, args, stack, depth, path):
    key_type, val_type = args if args else (str, Any)
    mo_validation_kit.ensure_type(value, dict, path, is_aggregate=True)
    for k, v in value.items():
        mo_validation_kit.ensure_type(
            k,
            key_type,
            msg=f"{path} key must be {key_type.__name__}",
            is_aggregate=True,
        )
        stack.append((v, val_type, depth + 1, f"{path}.{k}"))


def _handle_dict_shorthand(value, sch, origin, args, stack, depth, path):
    mo_validation_kit.ensure_type(value, dict, path, is_aggregate=True)
    for k, subschema in sch.items():
        mo_validation_kit.ensure_in(
            k, value, msg=f"Missing key '{k}' in {path}", is_aggregate=True
        )
        stack.append((value[k], subschema, depth + 1, f"{path}.{k}"))
