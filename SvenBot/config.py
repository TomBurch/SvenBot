from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    ARCHUB_TOKEN: str
    BOT_TOKEN: str
    CLIENT_ID: str
    PUBLIC_KEY: str
    GITHUB_TOKEN: str

    STEAM_MODLIST: int

    ANNOUNCE_CHANNEL: int
    OP_CHANNEL: int
    TEST_CHANNEL: int
    STAFF_CHANNEL: int

    ADMIN_ROLE: int
    MEMBER_ROLE: int
    RECRUIT_ROLE: int

    class Config:
        env_file = ".env"


settings = Settings()

EVENT_PINGS = {
    'main': [settings.MEMBER_ROLE, settings.OP_CHANNEL],
    'recruit': [settings.RECRUIT_ROLE, settings.OP_CHANNEL]
}
