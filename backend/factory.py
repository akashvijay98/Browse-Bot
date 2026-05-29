from langchain_core.language_models.chat_models import BaseChatModel
from config import ACTIVE_PROVIDER, MODEL_CONFIGS

class LLMFactory:
    @staticmethod
    def build() -> BaseChatModel:
        config = MODEL_CONFIGS.get(ACTIVE_PROVIDER)
        
        if ACTIVE_PROVIDER == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=config["model_name"],
                google_api_key=config["api_key"],
                temperature=0
            )
        
        elif ACTIVE_PROVIDER == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config["model_name"],
                base_url=config["base_url"],
                num_ctx=config["num_ctx"],
                temperature=0,
                format="json"
            )
            
        raise ValueError(f"Provider {ACTIVE_PROVIDER} is not supported or configured.")