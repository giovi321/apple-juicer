"""Cross-artifact identity correlation.

Communication artifacts each carry a counterparty identifier in a different
shape — a WhatsApp JID, an iMessage handle, a dialled number, a voicemail
sender. ``normalize_identifier`` collapses these to one comparable key so a
person's activity can be grouped across artifacts.
"""

from core.correlation.identity import identity_key, normalize_identifier

__all__ = ["identity_key", "normalize_identifier"]
