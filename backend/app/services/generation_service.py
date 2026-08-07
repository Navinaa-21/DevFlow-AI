import logging
from sqlalchemy.orm import Session
from app.repositories.commit_repository import CommitRepository
from app.repositories.commit_summary_repository import CommitSummaryRepository
from app.repositories.documentation_repository import DocumentationRepository
from app.repositories.ai_generation_repository import AIGenerationRepository
from app.services.ai_service import AIService
from app.models.commit import Commit

logger = logging.getLogger(__name__)

class GenerationService:
    """
    Service responsible for coordinating with AI services to summarize commits and
    generate technical documentation, while persisting all states and outputs in the database.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes the GenerationService with database Session and necessary repositories.

        Args:
            db (Session): The synchronous SQLAlchemy database session.
        """
        self.db = db
        self.commit_repo = CommitRepository(db)
        self.ai_gen_repo = AIGenerationRepository(db)
        self.summary_repo = CommitSummaryRepository(db)
        self.doc_repo = DocumentationRepository(db)
        self.ai_service = AIService()

    async def generate_for_commit(self, commit: Commit) -> None:
        """
        Coordinates the full AI generation pipeline for a given Commit.
        
        Workflow:
        1. Create an AIGeneration record with status="QUEUED".
        2. Generate commit summary using AIService.
        3. Save CommitSummary to the database.
        4. Generate documentation from the summary.
        5. Save Documentation to the database.
        6. Update AIGeneration status to SUCCESS.
        7. On failure, update status to FAILED and re-raise.

        Args:
            commit (Commit): The commit database model object.

        Raises:
            Exception: Re-raises any exception encountered during the workflow,
                      after marking the tracking status to FAILED.
        """
        logger.info(f"Starting AI generation pipeline for commit {commit.sha}")
        
        # 1. Create an AIGeneration record with status="QUEUED"
        ai_gen = self.ai_gen_repo.create_generation(
            commit_id=commit.id,
            provider="groq",
            status="QUEUED"
        )
        
        try:
            # Safely fetch diff content if stored or attached to the commit object,
            # otherwise default to an empty string.
            diff_content = getattr(commit, "diff_content", "") or getattr(commit, "diff", "") or ""
            
            # If diff_content is empty (e.g. for real webhook commits), attempt to fetch it from GitHub
            if not diff_content:
                user = commit.repository.user if commit.repository else None
                if user:
                    try:
                        from app.services.github_service import GithubService
                        github_service = GithubService(self.db, user)
                        diff_content = github_service.fetch_commit_diff(
                            commit.repository.owner,
                            commit.repository.name,
                            commit.sha
                        )
                        logger.info(f"Successfully fetched diff content from GitHub for commit {commit.sha} (length: {len(diff_content)})")
                    except Exception as e:
                        logger.error(f"Failed to fetch commit diff from GitHub: {str(e)}")
            
            # 2. Generate commit summary using AIService
            logger.info(f"Generating summary for commit {commit.sha}")
            summary_text = await self.ai_service.summarize_commit(commit.message, diff_content)
            
            # 3. Save CommitSummary
            logger.info(f"Saving summary for commit {commit.sha}")
            self.summary_repo.create_summary(
                commit_id=commit.id,
                summary_text=summary_text
            )
            
            # 4. Generate documentation from the summary
            logger.info(f"Generating documentation for commit {commit.sha}")
            doc_text = await self.ai_service.generate_documentation(summary_text)
            
            # 5. Save Documentation
            logger.info(f"Saving documentation for commit {commit.sha}")
            self.doc_repo.create_documentation(
                commit_id=commit.id,
                markdown=doc_text
            )
            
            # 6. Update AIGeneration status to SUCCESS
            logger.info(f"AI generation pipeline completed successfully for commit {commit.sha}")
            self.ai_gen_repo.update_status(
                generation_id=ai_gen.id,
                status="SUCCESS"
            )
            
        except Exception as e:
            logger.error(f"AI generation pipeline failed for commit {commit.sha}: {str(e)}", exc_info=True)
            # 7. On failure, update status to FAILED
            try:
                self.ai_gen_repo.update_status(
                    generation_id=ai_gen.id,
                    status="FAILED"
                )
            except Exception as update_err:
                logger.error(f"Failed to update AIGeneration status to FAILED: {str(update_err)}")
            
            # Re-raise original exception to ensure callers are notified of pipeline failure
            raise e
