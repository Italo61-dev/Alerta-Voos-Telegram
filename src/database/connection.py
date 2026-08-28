import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator, Any
from src.config import Config

class DatabaseManager:
    def __init__(self, config: Config):
        self.config = config

    def _connect(self) -> Any:
        if self.config.turso_database_url and self.config.turso_auth_token:
            try:
                import libsql
                return libsql.connect(
                    self.config.turso_database_url,
                    auth_token=self.config.turso_auth_token
                )
            except Exception as e:
                logging.error(f"Falha ao conectar ao Turso Cloud: {e}. Alternando para SQLite local.")

        return sqlite3.connect(self.config.db_path)

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass
