from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.backupfs.types import BackupStatus
from core.db.base import Base


class DecryptionStatus(str, enum.Enum):
    PENDING = "pending"
    DECRYPTING = "decrypting"
    DECRYPTED = "decrypted"
    FAILED = "failed"


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ios_identifier: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[BackupStatus] = mapped_column(
        Enum(BackupStatus, native_enum=False, create_constraint=True), default=BackupStatus.DISCOVERED
    )
    decryption_status: Mapped[DecryptionStatus] = mapped_column(
        Enum(DecryptionStatus, native_enum=False, create_constraint=True), default=DecryptionStatus.PENDING
    )
    decrypted_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    decryption_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    decrypted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexing_progress: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=0)
    indexing_total: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=0)
    indexing_artifact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def mark_seen(self) -> None:
        self.last_seen_at = datetime.utcnow()
