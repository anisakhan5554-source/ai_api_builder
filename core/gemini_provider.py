import os
from dotenv import load_dotenv
from google import genai
from core.ai_provider import AIProvider

load_dotenv()
print("GEMINI KEY:", os.environ.get("GEMINI_API_KEY"))

_client = None

def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client

class GeminiProvider(AIProvider):

    async def generate(self, prompt: str) -> str:
        client = get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text

    async def generate_code(self, description: str) -> str:
        prompt = f"Generate a FastAPI route for: {description}. Return only Python code."
        return await self.generate(prompt)

    async def generate_api_schema(self, description: str) -> dict:
        prompt = f"Generate a JSON schema for an API that: {description}. Return only valid JSON."
        result = await self.generate(prompt)
        return {"schema": result}