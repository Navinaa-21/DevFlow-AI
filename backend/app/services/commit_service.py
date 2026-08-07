import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.commit_repository import CommitRepository
from app.services.generation_service import GenerationService
from app.models.commit import Commit

logger = logging.getLogger(__name__)


class CommitService:
    """
    Orchestrator service handling high-level commit processing and workflow coordination.
    Iterates through groups of incoming commits and triggers AI generation pipelines.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes CommitService with a database session, repository, and generation service.

        Args:
            db (Session): The synchronous SQLAlchemy database session.
        """
        self.db = db
        self.commit_repo = CommitRepository(db)
        self.generation_service = GenerationService(db)

    async def handle_new_commits(self, commits: List[Commit]) -> Dict[str, Any]:
        """
        Iterates through the list of commits, triggering the AI Generation pipeline for each.
        Gracefully handles failures of individual commits so that a single failure
        does not stop processing for subsequent commits.

        Args:
            commits (List[Commit]): A list of Commit database model objects to process.

        Returns:
            Dict[str, Any]: A dictionary containing processing statistics:
                - "total": The total number of commits processed.
                - "successful": The number of successfully processed commits.
                - "failed": The number of commits that failed processing.
                - "failures": A list of dicts with commit "sha" and "error" description.
        """
        stats = {
            "total": len(commits),
            "successful": 0,
            "failed": 0,
            "failures": []
        }

        logger.info(f"Starting batch processing of {stats['total']} commits.")

        for commit in commits:
            try:
                logger.info(f"Processing commit {commit.sha}...")
                await self.generation_service.generate_for_commit(commit)
                stats["successful"] += 1
                logger.info(f"Successfully processed commit {commit.sha}.")
            except Exception as e:
                stats["failed"] += 1
                error_msg = str(e)
                logger.error(f"Failed to process commit {commit.sha}: {error_msg}", exc_info=True)
                stats["failures"].append({
                    "sha": commit.sha,
                    "error": error_msg
                })

        logger.info(
            f"Finished batch processing. "
            f"Total: {stats['total']}, "
            f"Successful: {stats['successful']}, "
            f"Failed: {stats['failed']}."
        )
        return stats

    async def process_commit(self, commit_id: Any) -> None:
        """
        Coordinates the background analysis of a single commit by its database ID.

        Args:
            commit_id (Any): The ID (typically UUID) of the commit to retrieve and process.
        """
        commit = self.db.query(Commit).filter(Commit.id == commit_id).first()
        if not commit:
            raise ValueError(f"Commit with ID {commit_id} not found.")
        
        await self.generation_service.generate_for_commit(commit)
