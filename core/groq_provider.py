import os
from dotenv import load_dotenv
from groq import Groq
from groq.types.chat import ChatCompletion
from core.ai_provider import AIProvider

load_dotenv()

_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        _groq_client = Groq(api_key=api_key)
    return _groq_client

class GroqProvider(AIProvider):

    async def generate(self, prompt: str) -> str:
        client = get_groq_client()
        response: ChatCompletion = client.chat.completions.create(
            model="llama-3.3-70b-Versatile",
            messages=[
                {"role": "user", "content": prompt}
            ]
        ) # type: ignore
        return str(response.choices[0].message.content)

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
    - Follow OpenAPI 3.0 structure exactly (openapi, info, paths, components)
    - Include realistic paths, methods, request bodies, and response schemas
    - Return only the raw JSON, no markdown, no explanation, no code fences"""

        result = await self.generate(prompt)
        return {"openapi_spec": result}