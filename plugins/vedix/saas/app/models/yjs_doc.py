"""``yjs_docs`` table — durable snapshot store for Yjs CRDT documents.

Each row pins a single Yjs document — either a federated palace drawer
(``kind="palace_drawer"``), a collaboratively edited manuscript
(``kind="manuscript"``), or a CRDT-backed comment thread
(``kind="comment_thread"``) — to a binary state vector. The websocket
server (``app.workers.yjs_server``) periodically encodes the active
in-memory ``YDoc`` and writes the blob to ``state_vector`` so a server
restart can rehydrate the document without losing edits.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import GUID, Base


class YjsDoc(Base):
    __tablename__ = "yjs_docs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    # logical document id used in the WS URL (/doc/{doc_id})
    doc_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    # palace_drawer | manuscript | comment_thread
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    # opaque Yjs binary snapshot; bytes() if the doc has never been written
    state_vector: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, default=bytes
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
