from enum import Enum


class AuthProvider(str, Enum):
    LOCAL = "LOCAL"
    GITHUB = "GITHUB"
    GOOGLE = "GOOGLE"
    AZURE = "AZURE"


class WorkspaceRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    DEVELOPER = "DEVELOPER"


class RepositoryProvider(str, Enum):
    GITHUB = "GITHUB"
    GITLAB = "GITLAB"
    AZURE_DEVOPS = "AZURE_DEVOPS"


class InvitationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CommitStatus(str, Enum):
    """Processing lifecycle state for an ingested commit record."""
    PENDING    = "PENDING"     # Newly ingested — awaiting downstream processing
    PROCESSING = "PROCESSING"  # Picked up by background worker
    COMPLETED  = "COMPLETED"   # All downstream tasks completed successfully
    FAILED     = "FAILED"      # Downstream processing failed after retries


class WebhookProcessingStatus(str, Enum):
    """Processing state for a raw webhook_event row."""
    RECEIVED  = "RECEIVED"   # Raw event stored, not yet processed
    PROCESSED = "PROCESSED"  # Commits extracted and stored successfully
    IGNORED   = "IGNORED"    # Non-push event — verified, logged, acknowledged
    FAILED    = "FAILED"     # Processing attempted but failed


class WebhookEventType(str, Enum):
    """GitHub webhook event types relevant to this system."""
    PUSH  = "push"   # Actively processed — commits extracted
    PING  = "ping"   # Webhook registration confirmation
    OTHER = "other"  # Any other unrecognised GitHub event type