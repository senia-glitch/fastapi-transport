"""Numeric error-code resolution.

Resolution walks the MRO of the exception, so subclasses inherit the code
of their nearest mapped ancestor.

Two-phase lookup:
  1. Class identity against ``_CLASS_CODES`` (built-in exceptions — no
     name collision possible).
  2. Class name against the user-supplied mapping (backward-compatible
     with ``FAT_ERROR_CODES`` env var).
"""

from fastbase.errors.exceptions import (
    BaseHTTPError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

# ── built-in exceptions mapped by class identity (collision-safe) ──────
_CLASS_CODES: dict[type, int] = {
    BaseHTTPError: 3000,
    NotFoundError: 3001,
    ValidationError: 3002,
    ConflictError: 3003,
    UnauthorizedError: 3004,
    ForbiddenError: 3005,
    InternalError: 3500,
}

# ── string-based mapping kept for backward-compatible env var parsing ──
DEFAULT_ERROR_CODES: dict[str, int] = {
    cls.__name__: code for cls, code in _CLASS_CODES.items()
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
      1. explicit ``exc.code`` set in ``__init__``;
      2. explicit ``exc.default_code`` on the class;
      3. first matching class name in ``type(exc).__mro__`` via the
         user-supplied *mapping* (includes overrides from
         ``FAT_ERROR_CODES``);
      4. first matching class via class identity against built-in
         exceptions (collision-safe);
      5. *fallback*.
    """
    explicit = getattr(exc, "code", None)
    if explicit is not None:
        return explicit

    default = getattr(exc, "default_code", None)
    if default is not None:
        return default

    # Phase 1: name-based lookup (user overrides win).
    for cls in type(exc).__mro__:
        if cls.__name__ in mapping:
            return mapping[cls.__name__]

    # Phase 2: class identity (safe for built-in exceptions).
    for cls in type(exc).__mro__:
        if cls in _CLASS_CODES:
            return _CLASS_CODES[cls]

    return fallback
