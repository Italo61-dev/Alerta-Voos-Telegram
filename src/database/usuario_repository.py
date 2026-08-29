import logging
from typing import List, Optional
from src.database.connection import DatabaseManager
from src.models.usuario import Usuario

class UsuarioRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def is_autorizado(self, user_id: int) -> bool:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT autorizado FROM usuarios WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return bool(row and row[0] == 1)
        except Exception as e:
            logging.error(f"Erro ao verificar autorização do usuário {user_id}: {e}")
            return False

    def registrar_solicitacao(self, user_id: int, nome: str, username: str) -> None:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO usuarios (user_id, nome, username, autorizado)
                    VALUES (?, ?, ?, 0)
                """, (user_id, nome, username))
        except Exception as e:
            logging.error(f"Erro ao registrar solicitação para {user_id}: {e}")

    def definir_autorizacao(self, user_id: int, autorizado: bool) -> bool:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE usuarios SET autorizado = ? WHERE user_id = ?",
                    (1 if autorizado else 0, user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao definir autorização de {user_id}: {e}")
            return False

    def listar_autorizados(self) -> List[Usuario]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, nome, username, autorizado, criado_em FROM usuarios WHERE autorizado = 1 ORDER BY criado_em DESC"
                )
                rows = cursor.fetchall()
                return [
                    Usuario(
                        user_id=r[0],
                        nome=r[1] or "Sem Nome",
                        username=r[2] or "",
                        autorizado=True,
                        criado_em=str(r[4]) if r[4] else None
                    )
                    for r in rows
                ]
        except Exception as e:
            logging.error(f"Erro ao listar usuários autorizados: {e}")
            return []

    def listar_todos(self) -> List[Usuario]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id, nome, username, autorizado, criado_em FROM usuarios ORDER BY criado_em DESC"
                )
                rows = cursor.fetchall()
                return [
                    Usuario(
                        user_id=r[0],
                        nome=r[1] or "Sem Nome",
                        username=r[2] or "",
                        autorizado=bool(r[3] == 1),
                        criado_em=str(r[4]) if r[4] else None
                    )
                    for r in rows
                ]
        except Exception as e:
            logging.error(f"Erro ao listar usuários: {e}")
            return []
