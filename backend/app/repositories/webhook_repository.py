import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent
from app.models.enums import WebhookProcessingStatus
from app.repositories.base import BaseRepository


class WebhookRepository(BaseRepository[WebhookEvent]):
    """
    Repository handling all database access for the WebhookEvent model.

    Responsibilities:
        - Persisting raw inbound webhook event records.
        - Idempotency lookups by GitHub delivery_id.
        - Updating processing state (status, timestamps, error messages).
        - Listing events for audit and observability.

    This class contains ONLY database access logic.
    Business rules, routing, and error handling belong in the service layer.
    """

    def __init__(self, db: Session):
        super().__init__(WebhookEvent, db)

    # ── Write Operations ────────────────────────────────────────────────────────

    def create_webhook_event(
        self,
        repository_id: UUID,
        event_type: str,
        delivery_id: str,
        payload: dict,
    ) -> WebhookEvent:
        """
        Persist a raw inbound webhook event record immediately.

        Called in Transaction 1 of the two-phase ingestion pipeline — before any
        commit extraction. The event is stored with processing_status=RECEIVED
        and processed=False so it is visible in audit logs regardless of whether
        downstream processing succeeds or fails.

        Args:
            repository_id: UUID of the connected repository.
            event_type:    Raw value of the X-GitHub-Event header (e.g. "push").
            delivery_id:   Value of the X-GitHub-Delivery header — idempotency key.
            payload:       Full raw request body parsed as a dict (JSONB).

        Returns:
            The persisted WebhookEvent ORM object with a populated id.
        """
        event = WebhookEvent(
            repository_id=repository_id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
            processed=False,
            processing_status=WebhookProcessingStatus.RECEIVED,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update_processing_status(
        self,
        event: WebhookEvent,
        status: WebhookProcessingStatus,
        processed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> WebhookEvent:
        """
        Update the processing_status of an existing WebhookEvent record.

        Used by the service layer to transition a webhook event through its
        lifecycle states: RECEIVED → PROCESSED | IGNORED | FAILED.

        Args:
            event:         The WebhookEvent ORM object to update.
            status:        The new WebhookProcessingStatus value.
            processed_at:  Timestamp of completion (set for PROCESSED and IGNORED).
            error_message: Error detail string (set for FAILED).

        Returns:
            The refreshed WebhookEvent ORM object.
        """
        event.processing_status = status
        event.processed = status in (
            WebhookProcessingStatus.PROCESSED,
            WebhookProcessingStatus.IGNORED,
        )
        if processed_at is not None:
            event.processed_at = processed_at
        if error_message is not None:
            event.error_message = error_message
        self.db.commit()
        self.db.refresh(event)
        return event

    def mark_processed(self, event: WebhookEvent) -> WebhookEvent:
        """
        Convenience method: transition a webhook event to PROCESSED state.

        Sets processing_status=PROCESSED, processed=True, and
        processed_at to the current UTC timestamp.

        Args:
            event: The WebhookEvent ORM object to mark as processed.

        Returns:
            The refreshed WebhookEvent ORM object.
        """
        return self.update_processing_status(
            event=event,
            status=WebhookProcessingStatus.PROCESSED,
            processed_at=datetime.now(timezone.utc),
        )

    def mark_failed(self, event: WebhookEvent, error_message: str) -> WebhookEvent:
        """
        Convenience method: transition a webhook event to FAILED state.

        Sets processing_status=FAILED, processed=False, and populates
        error_message for observability and reprocessing support.

        Args:
            event:         The WebhookEvent ORM object to mark as failed.
            error_message: Human-readable description of the failure.

        Returns:
            The refreshed WebhookEvent ORM object.
        """
        return self.update_processing_status(
            event=event,
            status=WebhookProcessingStatus.FAILED,
            error_message=error_message,
        )

    def mark_ignored(self, event: WebhookEvent) -> WebhookEvent:
        """
        Convenience method: transition a non-push event to IGNORED state.

        Used for all non-push event types (ping, pull_request, etc.) that pass
        signature verification but require no commit extraction. Sets
        processing_status=IGNORED, processed=True, processed_at=now.

        Args:
            event: The WebhookEvent ORM object to mark as ignored.

        Returns:
            The refreshed WebhookEvent ORM object.
        """
        return self.update_processing_status(
            event=event,
            status=WebhookProcessingStatus.IGNORED,
            processed_at=datetime.now(timezone.utc),
        )

    # ── Read Operations ─────────────────────────────────────────────────────────

    def get_by_delivery_id(self, delivery_id: str) -> Optional[WebhookEvent]:
        """
        Fetch a WebhookEvent by its GitHub delivery_id.

        Used for idempotency checking — if a record exists for this delivery_id,
        the event was already received and must not be re-processed.

        Uses the ix_webhook_events_delivery_id unique index for O(1) lookup.

        Args:
            delivery_id: Value of the X-GitHub-Delivery header.

        Returns:
            The matching WebhookEvent or None if not found.
        """
        statement = select(WebhookEvent).where(
            WebhookEvent.delivery_id == delivery_id
        )
        return self.db.scalars(statement).first()

    def get_by_event_id(self, event_id: UUID) -> Optional[WebhookEvent]:
        """
        Fetch a WebhookEvent by its internal UUID primary key.

        Args:
            event_id: The UUID primary key of the webhook event record.

        Returns:
            The matching WebhookEvent or None if not found.
        """
        return self.db.get(WebhookEvent, event_id)

    def list_events_by_repository(
        self,
        repository_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[WebhookEvent]:
        """
        List webhook events for a specific repository ordered by most recent first.

        Uses the ix_webhook_events_repository_id index. Intended for audit and
        operational dashboards showing delivery history per repository.

        Args:
            repository_id: UUID of the repository.
            skip:          Number of records to skip (pagination offset).
            limit:         Maximum number of records to return (max 50 by default).

        Returns:
            Sequence of WebhookEvent ORM objects, newest first.
        """
        statement = (
            select(WebhookEvent)
            .where(WebhookEvent.repository_id == repository_id)
            .order_by(desc(WebhookEvent.created_at))
            .offset(skip)
            .limit(limit)
        )
        return self.db.scalars(statement).all()
