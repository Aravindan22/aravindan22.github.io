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
        self.model_type = "gemini-3-flash-preview"
        # https://ai.google.dev/gemini-api/docs/models#all-gemini-3-models
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
                api_key=self.nvidia_api_key, 
                timeout=90,
                )

class CloudFlareModel:
    def __init__(self):
        print("Using Cloudflare Model")
        # https://developers.cloudflare.com/workers-ai/platform/pricing/#llm-model-pricing
        from langchain_cloudflare.chat_models import ChatCloudflareWorkersAI
        self.cloudflare_api_key = os.environ['CLOUDFLARE_API_TOKEN']
        self.cloudflare_acc_id= os.environ['CLOUDFLARE_ACCOUNT_ID']
        self.model_type= "@cf/zai-org/glm-4.7-flash"
        self.model_type= "@cf/ibm-granite/granite-4.0-h-micro"
        self.model_type= "@cf/meta/llama-3.2-1b-instruct"
        self.model_type= "@cf/qwen/qwen3-30b-a3b-fp8"
        self.model = ChatCloudflareWorkersAI(
                account_id=self.cloudflare_acc_id,
                api_token=self.cloudflare_api_key,
                model=self.model_type
                )

model = None

if CURRENT_MODEL == "nvidia":
    model = NvidiaModel().model
elif CURRENT_MODEL == "gemini":
    model = GeminiModel().model
elif CURRENT_MODEL == "cloudflare":
    model = CloudFlareModel().model
