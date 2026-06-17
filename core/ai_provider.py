from abc import ABC, abstractmethod

class AIProvider(ABC):

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def generate_code(self, description: str) -> str:
        pass

    @abstractmethod
    async def generate_api_schema(self, description: str) -> dict:
        pass