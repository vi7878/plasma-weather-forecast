import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_KEY = os.getenv("OWM_API_KEY")
    API_URL = os.getenv("OWM_API_URL", "https://api.openweathermap.org/data/2.5/forecast")
    GEO_URL = os.getenv("OWM_GEO_URL", "https://api.openweathermap.org/geo/1.0/direct")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "weather_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    @classmethod
    def validate(cls):
        if not cls.API_KEY:
            raise ValueError("OWM_API_KEY не знайдено у змінних середовища або файлі .env")
