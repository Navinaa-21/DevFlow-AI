from pydantic import BaseModel

class DashboardStatsResponse(BaseModel):
    total_repositories: int
    total_commits_processed: int
    active_ai_models: int
    documentation_pages: int
