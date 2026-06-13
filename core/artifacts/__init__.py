"""Artifact registry: one ArtifactSpec per supported iOS artifact type."""

from core.artifacts.ingest import truncate_artifacts
from core.artifacts.registry import REGISTRY, decrypt_targets, filename_to_key
from core.artifacts.spec import ArtifactSpec

__all__ = [
    "ArtifactSpec",
    "REGISTRY",
    "decrypt_targets",
    "filename_to_key",
    "truncate_artifacts",
]
