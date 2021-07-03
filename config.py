from pydantic import BaseSettings

class Settings(BaseSettings):
    ARCHUB_TOKEN: str
    BOT_TOKEN: str
    CLIENT_ID: str
    PUBLIC_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()