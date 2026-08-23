import os
from dotenv import load_dotenv
load_dotenv()

from .settings import CURRENT_MODEL

class GeminiModel:
    def __init__(self):
        if "GOOGLE_API_KEY" not in os.environ:
            print("No ENV key")
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.model_type = "gemini-3.6-flash"
        self.model_type = "gemini-3.5-flash"
        self.model = ChatGoogleGenerativeAI(
            model=self.model_type,
            temperature=1.0,  # Gemini 3.0+ defaults to 1.0
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )

class NvidiaModel:
    def __init__(self):
        print("Using Nvidia Model")
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        # self.model_type = "nvidia/nemotron-3.5-lightning-30b-a3b"
        # self.model_type = "openai/gpt-oss-120b"
        # self.model_type = "meta/llama-3.2-3b-instruct"
        self.model_type = "google/gemma-4-31b-it"
        self.nvidia_api_key = os.environ['NVIDIA_API_KEY']
        self.model = ChatNVIDIA(
                model=self.model_type,
                # api_key="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", 
                api_key=self.nvidia_api_key, 
                timeout=90,
                )


model = None

if CURRENT_MODEL == "nvidia":
    model = NvidiaModel().model
elif CURRENT_MODEL == "gemini":
    model = GeminiModel().model
