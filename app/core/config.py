# app/core/config.py
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI
from langchain.embeddings import HuggingFaceInferenceAPIEmbeddings


class Settings(BaseSettings):
    # Main (Vendor / AI / Inventory) Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:onetable%40admin@db.wpnvxoyvmabgleczyqsm.supabase.co/postgres"

    # Second (Restaurant / Business Owner) Database
    RESTAURANT_DATABASE_URL: str = "postgresql+asyncpg://postgres:onetable%40admin@db.wpnvxoyvmabgleczyqsm.supabase.co/postgres"

    # Third (Vendor) Database
    VENDOR_DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@db.aollcrguvmslazlocrwj.supabase.co/postgres"

    # --- MongoDB (hardcoded) ---
    MONGO_URI: str = (
        "mongodb+srv://tahahasnat018:onetable%40admin"
        "@vendor.csyar25.mongodb.net/?retryWrites=true&w=majority&appName=Vendor"
    )
    MONGO_DB: str = "restaurant_agents"

    # --- API keys (hardcoded) ---
    GROQ_API_KEY: str = "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"
    HF_API_KEY: str = "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"
    ELEVENLABS_API_KEY: str = "sk_ac27e660f727c6032c4e875555250203e1c529600372341e"

    class Config:
        env_file = None


settings = Settings()

# --- LangChain models using your keys ---
llm = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY,
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.0,
)

llm_cohort = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY,
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.7,
)

llm_sales = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY,
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.9,
)

hf_embeddings = HuggingFaceInferenceAPIEmbeddings(
    api_key=settings.HF_API_KEY,
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
