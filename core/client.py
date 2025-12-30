from openai import AsyncOpenAI
from core.config import settings

def get_client():
    return AsyncOpenAI(
        api_key=settings.API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
