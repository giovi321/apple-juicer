"""The single source of truth for the supported iOS artifact types."""

from __future__ import annotations

from core.artifacts import ingest
from core.artifacts.spec import ArtifactSpec

# Ordered as the indexer runs them (photos first populates the search index).
REGISTRY: list[ArtifactSpec] = [
    ArtifactSpec(
        key="photos",
        db_filename="Photos.sqlite",
        source_domain="CameraRollDomain",
        source_relative_path="Media/PhotoData/Photos.sqlite",
        ingest=ingest.ingest_photos,
    ),
    ArtifactSpec(
        key="whatsapp",
        db_filename="ChatStorage.sqlite",
        source_domain="AppDomainGroup-group.net.whatsapp.WhatsApp.shared",
        source_relative_path="ChatStorage.sqlite",
        ingest=ingest.ingest_whatsapp,
    ),
    ArtifactSpec(
        key="messages",
        db_filename="chat.db",
        source_domain="HomeDomain",
        source_relative_path="Library/SMS/sms.db",
        ingest=ingest.ingest_messages,
    ),
    ArtifactSpec(
        key="notes",
        db_filename="notes.sqlite",
        source_domain="AppDomain-com.apple.mobilenotes",
        source_relative_path="Library/Notes/notes.sqlite",
        ingest=ingest.ingest_notes,
    ),
    ArtifactSpec(
        key="calendar",
        db_filename="Calendar.sqlite",
        source_domain="HomeDomain",
        source_relative_path="Library/Calendar/Calendar.sqlitedb",
        ingest=ingest.ingest_calendar,
    ),
    ArtifactSpec(
        key="contacts",
        db_filename="AddressBook.sqlitedb",
        source_domain="HomeDomain",
        source_relative_path="Library/AddressBook/AddressBook.sqlitedb",
        ingest=ingest.ingest_contacts,
    ),
    ArtifactSpec(
        key="calls",
        db_filename="CallHistory.storedata",
        source_domain="HomeDomain",
        source_relative_path="Library/CallHistoryDB/CallHistory.storedata",
        ingest=ingest.ingest_calls,
    ),
    ArtifactSpec(
        key="safari",
        db_filename="History.db",
        source_domain="AppDomainGroup-group.com.apple.safari",
        source_relative_path="Library/Safari/History.db",
        ingest=ingest.ingest_safari,
    ),
    ArtifactSpec(
        key="locations",
        db_filename="RoutineDCache.sqlite",
        source_domain="HomeDomain",
        source_relative_path="Library/Caches/com.apple.routined/Cache.sqlite",
        ingest=ingest.ingest_locations,
    ),
    ArtifactSpec(
        key="voicemail",
        db_filename="voicemail.db",
        source_domain="HomeDomain",
        source_relative_path="Library/Voicemail/voicemail.db",
        ingest=ingest.ingest_voicemail,
    ),
]


def filename_to_key() -> dict[str, str]:
    """Map an extracted DB filename back to its artifact key."""
    return {spec.db_filename: spec.key for spec in REGISTRY}


def decrypt_targets() -> list[tuple[str, str, str]]:
    """(source_domain, source_relative_path, output_filename) for each artifact."""
    return [(spec.source_domain, spec.source_relative_path, spec.db_filename) for spec in REGISTRY]
