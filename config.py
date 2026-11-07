
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load the .env file from the project directory.
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Let the project's .env values take precedence over stale
# Windows environment variables during local development.
load_dotenv(dotenv_path=ENV_FILE, override=True)


class Config:
    # Flask configuration
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "fallback_secret_for_dev_only"
    )

    # TiDB / MySQL configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "4000"))

    # Support both TiDB-generated and existing project variable names.
    DB_USER = (
        os.getenv("DB_USERNAME")
        or os.getenv("DB_USER")
        or "root"
    )

    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Support both DB_DATABASE and DB_NAME.
    DB_NAME = (
        os.getenv("DB_DATABASE")
        or os.getenv("DB_NAME")
        or "finance_db"
    )

    # Gemini configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    @staticmethod
    def validate():
        if (
            not Config.SECRET_KEY
            or Config.SECRET_KEY == "fallback_secret_for_dev_only"
        ):
            print("WARNING: Using fallback SECRET_KEY.")

        if not Config.DB_HOST:
            raise ValueError("DB_HOST is missing from .env")

        if not Config.DB_USER or Config.DB_USER == "root":
            raise ValueError(
                "Invalid DB username. Check DB_USERNAME or DB_USER "
                "in your .env file. TiDB requires the cluster prefix."
            )

        if not Config.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is missing from .env")

        if not Config.DB_NAME:
            raise ValueError("DB_NAME or DB_DATABASE is missing.")
