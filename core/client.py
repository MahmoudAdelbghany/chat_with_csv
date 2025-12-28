from openai import OpenAI
from core.config import settings

def get_client():
    return OpenAI(
        api_key=settings.API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

