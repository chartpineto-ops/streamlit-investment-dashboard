from __future__ import annotations


def status_from_warnings(warnings: list[str], required_ok: bool = True) -> str:
    if not required_ok:
        return "Invalid"
    return "Partial" if warnings else "Valid"


def missing_fields(mapping: dict, fields: list[str]) -> list[str]:
    return [field for field in fields if mapping.get(field) in (None, "", "N/A")]

