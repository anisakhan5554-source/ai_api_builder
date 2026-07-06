import os
from dotenv import load_dotenv
import anthropic
from core.ai_provider import AIProvider

load_dotenv()

_claude_client = None

def get_claude_client():
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
    return _claude_client

class ClaudeProvider(AIProvider):

    async def generate(self, prompt: str) -> str:
        client = get_claude_client()
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    async def generate_code(self, description: str) -> str:
        prompt = f"""Generate a clean FastAPI route for: {description}

Requirements:
- Include all necessary imports
- Add proper error handling
- Add comments explaining each part
- Return clean, production-ready code
- No markdown, just pure Python code"""
        return await self.generate(prompt)

    async def generate_api_schema(self, description: str) -> dict:
        prompt = f"""Generate a valid OpenAPI 3.0 specification in JSON format for an API that: {description}

Requirements:
- Follow OpenAPI 3.0 structure exactly
- Include realistic paths, methods, request bodies, and response schemas
- Return only the raw JSON, no markdown, no explanation"""
        result = await self.generate(prompt)
        return {"openapi_spec": result}