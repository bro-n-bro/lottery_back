from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    SECRET_KEY: str
    GRPC_ADDRESS: str

    class Config:
        env_file = ".env"

settings = Settings()
