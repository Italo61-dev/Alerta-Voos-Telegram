import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
DEFAULT_DB_PATH = BASE_DIR / "alertas.db"

@dataclass(frozen=True)
class Config:
    telegram_token: str
    admin_id: int
    gemini_api_key: Optional[str]
    turso_database_url: Optional[str]
    turso_auth_token: Optional[str]
    check_interval_hours: int
    port: int
    db_path: Path
    max_alertas_por_usuario: int = 10

def _carregar_arquivo_env():
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k and k not in os.environ:
                        os.environ[k] = v

def load_config() -> Config:
    _carregar_arquivo_env()

    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "TELEGRAM_TOKEN não configurado! "
            "Defina a variável no arquivo .env ou nas variáveis de ambiente do sistema/Heroku."
        )

    admin_id_raw = os.environ.get("ADMIN_ID", "5599506814").strip()
    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        admin_id = 5599506814

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or None
    turso_url = os.environ.get("TURSO_DATABASE_URL", "").strip() or None
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "").strip() or None

    try:
        check_interval = int(os.environ.get("CHECK_INTERVAL_HOURS", 3))
    except ValueError:
        check_interval = 3

    try:
        port = int(os.environ.get("PORT", 8080))
    except ValueError:
        port = 8080

    try:
        max_alertas = int(os.environ.get("MAX_ALERTAS_POR_USUARIO", 10))
    except ValueError:
        max_alertas = 10

    return Config(
        telegram_token=token,
        admin_id=admin_id,
        gemini_api_key=gemini_key,
        turso_database_url=turso_url,
        turso_auth_token=turso_token,
        check_interval_hours=check_interval,
        port=port,
        db_path=DEFAULT_DB_PATH,
        max_alertas_por_usuario=max_alertas,
    )
