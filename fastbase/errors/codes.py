"""Numeric error-code resolution.

Mapping is: class name -> int. Resolution walks the MRO of the exception,
so subclasses inherit the code of their nearest mapped ancestor.
"""

DEFAULT_ERROR_CODES: dict[str, int] = {
    "BaseHTTPError": 3000,
    "NotFoundError": 3001,
    "ValidationError": 3002,
    "ConflictError": 3003,
    "UnauthorizedError": 3004,
    "ForbiddenError": 3005,
    "InternalError": 3500,
}

DEFAULT_FALLBACK_CODE = 3500


def merge_mappings(user: dict[str, int]) -> dict[str, int]:
    """Return a merged mapping: package defaults overridden by user values."""
    return {**DEFAULT_ERROR_CODES, **user}


def resolve_code(
    exc: BaseException,
    mapping: dict[str, int],
    fallback: int,
) -> int:
    """Resolve a numeric code for an exception.

    Order:
      1. explicit `exc.code` set in __init__;
      2. explicit `exc.default_code` on the class;
      3. first matching class name in type(exc).__mro__;
      4. fallback.
    """
    explicit = getattr(exc, "code", None)
    if explicit is not None:
        return explicit

    default = getattr(exc, "default_code", None)
    if default is not None:
        return default

    for cls in type(exc).__mro__:
        if cls.__name__ in mapping:
            return mapping[cls.__name__]

    return fallback