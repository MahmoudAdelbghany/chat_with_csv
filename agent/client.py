from openai import OpenAI
import os
from dotenv import load_dotenv


def get_client():
    load_dotenv()
    return OpenAI(
        api_key=os.getenv("openrouter"),
        base_url="https://openrouter.ai/api/v1",
    )

