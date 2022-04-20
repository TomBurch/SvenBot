from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    ARCHUB_TOKEN: str
    BOT_TOKEN: str
    CLIENT_ID: str
    PUBLIC_KEY: str
    GITHUB_TOKEN: str

    STAFF_CHANNEL: int

    ADMIN_ROLE: int

    class Config:
        env_file = ".env"


settings = Settings()
