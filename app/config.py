from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    google_client_id: str
    google_client_secret: str
    poppler_path: str

    class Config:
        env_file = ".env"

settings = Settings()