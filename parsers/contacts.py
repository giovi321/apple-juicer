from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from .base import apple_timestamp, sqlite_connection, table_exists


@dataclass(slots=True)
class ContactRecord:
    identifier: str
    first_name: str | None
    last_name: str | None
    company: str | None
    emails: list[str]
    phones: list[str]
    created_at: datetime | None
    updated_at: datetime | None
    avatar_file_id: str | None


def parse_contacts(db_path: Path) -> List[ContactRecord]:
    if not db_path.exists():
        return []

    with sqlite_connection(db_path) as conn:
        if not table_exists(conn, "ABPerson"):
            return []

        multi_values = _load_multi_values(conn)

        rows = conn.execute(
            """
            SELECT
                ABPerson.ROWID AS person_id,
                ABPerson.First,
                ABPerson.Last,
                ABPerson.Organization,
                ABPerson.CreationDate,
                ABPerson.ModificationDate,
                ABPerson.ImageURI
            FROM ABPerson
            """
        ).fetchall()

        contacts: list[ContactRecord] = []
        for row in rows:
            person_id = row["person_id"]
            identifier = f"contact-{person_id}"
            emails = multi_values.get((person_id, "Email"), [])
            phones = multi_values.get((person_id, "Phone"), [])

            contacts.append(
                ContactRecord(
                    identifier=identifier,
                    first_name=row["First"],
                    last_name=row["Last"],
                    company=row["Organization"],
                    emails=emails,
                    phones=phones,
                    created_at=apple_timestamp(row["CreationDate"]),
                    updated_at=apple_timestamp(row["ModificationDate"]),
                    avatar_file_id=row["ImageURI"],
                )
            )

    return contacts


def _load_multi_values(conn) -> dict[tuple[int, str], list[str]]:
    if not (table_exists(conn, "ABMultiValue") and table_exists(conn, "ABMultiValueLabel")):
        return {}
    label_rows = conn.execute("SELECT ROWID, value FROM ABMultiValueLabel").fetchall()
    label_lookup = {row["ROWID"]: row["value"] for row in label_rows}

    rows = conn.execute(
        """
        SELECT record_id, property, label, value
        FROM ABMultiValue
        """
    ).fetchall()

    values: dict[tuple[int, str], list[str]] = {}
    property_names = {
        3: "Phone",
        4: "Email",
        22: "URL",
    }

    for row in rows:
        property_name = property_names.get(row["property"])
        if not property_name:
            continue
        label_name = label_lookup.get(row["label"]) or property_name
        key = (row["record_id"], property_name)
        values.setdefault(key, []).append(row["value"])

    return values
