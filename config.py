from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    CAPTCHA_OPERATIONS: str = "+,-"  

    @property
    def captcha_operations_list(self) -> List[str]:
        return [op.strip() for op in self.CAPTCHA_OPERATIONS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

