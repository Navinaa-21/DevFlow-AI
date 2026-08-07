from typing import Optional
from groq import AsyncGroq, GroqError
from app.core.config import settings

class AIServiceError(Exception):
    """Exception raised when an AI service operation fails."""
    pass

class AIService:
    """
    Service wrapper for communication with the Groq Large Language Model (LLM) provider.
    This service is responsible only for interacting with the AI provider, initializing the client,
    and retrieving cleaned string outputs for summaries and documentation.
    """
    def __init__(self) -> None:
        """
        Initializes the AIService by setting up the Groq Async client once.
        Reads the API key and model name from settings.
        
        Raises:
            AIServiceError: If the GROQ_API_KEY is not set or configuration is missing.
        """
        if not settings.GROQ_API_KEY:
            raise AIServiceError("GROQ_API_KEY is not configured in settings.")
        
        try:
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize Groq client: {str(e)}")
        
        self.model_name = settings.GROQ_MODEL_NAME

    async def summarize_commit(self, commit_message: str, diff: str) -> str:
        """
        Generates a concise summary of changes by calling Groq LLM with the commit message and git diff.
        
        Args:
            commit_message (str): The original message of the git commit.
            diff (str): The git diff output showing file modifications.
            
        Returns:
            str: A clean, trimmed summary of the commit changes.
            
        Raises:
            AIServiceError: If the API call fails or receives an invalid response.
        """
        system_instruction = (
            "You are an AI assistant designed to summarize git commits. "
            "Given a commit message and its git diff, provide a clean, concise, and clear summary of the changes. "
            "Return only the summary. Do not include conversational filler, introductory remarks, or markdown headers."
        )
        user_prompt = f"Commit Message: {commit_message}\n\nDiff:\n{diff}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            
            if not response.choices:
                raise AIServiceError("Groq response returned no choices.")
                
            content = response.choices[0].message.content
            if content is None:
                raise AIServiceError("Groq response message content is empty.")
                
            return content.strip()
            
        except GroqError as e:
            raise AIServiceError(f"Groq API error during commit summarization: {str(e)}")
        except Exception as e:
            raise AIServiceError(f"Unexpected error during commit summarization: {str(e)}")

    async def generate_documentation(self, summary: str) -> str:
        """
        Generates technical documentation based on the provided commit summary.
        
        Args:
            summary (str): The summary of the commit changes.
            
        Returns:
            str: A clean, trimmed documentation string.
            
        Raises:
            AIServiceError: If the API call fails or receives an invalid response.
        """
        system_instruction = (
            "You are an AI assistant designed to generate structured developer documentation based on commit summaries.\n\n"
            "Generate documentation in clean Markdown format with the following sections:\n"
            "1. ## Overview\n"
            "   - Explain the overall purpose and context of the changes.\n"
            "2. ## Summary of Changes\n"
            "   - Describe the implemented features and capabilities.\n"
            "3. ## Files Changed\n"
            "   - Mention affected files and modules if the information is available or can be inferred.\n"
            "4. ## Technical Implementation\n"
            "   - Explain important classes, functions, workflows, and logical architectures.\n"
            "5. ## API Changes\n"
            "   - List endpoints, request/response models, and method changes (if applicable).\n"
            "6. ## Configuration Changes\n"
            "   - Detail any new environment variables, configuration settings, or database updates.\n"
            "7. ## Usage Examples\n"
            "   - Provide code snippets, curl commands, or command line usage examples (if applicable).\n"
            "8. ## Migration Notes\n"
            "   - Describe any steps needed to set up or deploy this change (e.g. running database migrations).\n"
            "9. ## Breaking Changes\n"
            "   - List potential compatibility risks or deprecated interfaces.\n\n"
            "Return only the Markdown documentation. Do not include introductory remarks, greetings, conversational filler, or final remarks."
        )
        user_prompt = f"Commit Summary:\n{summary}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            
            if not response.choices:
                raise AIServiceError("Groq response returned no choices.")
                
            content = response.choices[0].message.content
            if content is None:
                raise AIServiceError("Groq response message content is empty.")
                
            return content.strip()
            
        except GroqError as e:
            raise AIServiceError(f"Groq API error during documentation generation: {str(e)}")
        except Exception as e:
            raise AIServiceError(f"Unexpected error during documentation generation: {str(e)}")
