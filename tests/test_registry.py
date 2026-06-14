"""The artifact registry is the single source of truth for supported types,
so the worker/decrypt/route mappings cannot drift apart again.
"""

from __future__ import annotations

import inspect

from core.artifacts import REGISTRY, decrypt_targets, filename_to_key

EXPECTED_KEYS = {
    "photos",
    "whatsapp",
    "messages",
    "notes",
    "calendar",
    "contacts",
    "calls",
    "safari",
    "locations",
}


def test_registry_covers_expected_artifacts():
    assert {spec.key for spec in REGISTRY} == EXPECTED_KEYS


def test_keys_and_filenames_are_unique():
    keys = [spec.key for spec in REGISTRY]
    filenames = [spec.db_filename for spec in REGISTRY]
    assert len(keys) == len(set(keys))
    assert len(filenames) == len(set(filenames))


def test_filename_to_key_round_trips():
    mapping = filename_to_key()
    assert len(mapping) == len(REGISTRY)
    for spec in REGISTRY:
        assert mapping[spec.db_filename] == spec.key


def test_decrypt_targets_match_specs():
    targets = decrypt_targets()
    assert len(targets) == len(REGISTRY)
    for (domain, relative_path, filename), spec in zip(targets, REGISTRY):
        assert domain == spec.source_domain
        assert relative_path == spec.source_relative_path
        assert filename == spec.db_filename


def test_every_ingest_is_async():
    for spec in REGISTRY:
        assert inspect.iscoroutinefunction(spec.ingest)


def test_registry_keys_match_fixture_keys():
    """The synthetic fixture's artifact_files keys are exactly the registry keys."""
    from fixtures import build_all  # local import; tests dir is on sys.path

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        files = build_all(Path(tmp) / "decrypted")
    assert set(files) == EXPECTED_KEYS
