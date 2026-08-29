import logging
from typing import List, Optional
from src.database.connection import DatabaseManager
from src.models.alerta import Alerta

class AlertaRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def salvar(self, alerta: Alerta) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alertas (chat_id, origem, destino, teto, data_ida, data_volta, apenas_direto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alerta.chat_id,
                alerta.origem,
                alerta.destino,
                alerta.teto,
                alerta.data_ida,
                alerta.data_volta,
                1 if alerta.apenas_direto else 0
            ))
            return cursor.lastrowid

    def listar_por_usuario(self, chat_id: int) -> List[Alerta]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, chat_id, origem, destino, teto, data_ida, data_volta, ultimo_preco, apenas_direto, ativo, criado_em
                    FROM alertas
                    WHERE chat_id = ? AND ativo = 1
                    ORDER BY id DESC
                """, (chat_id,))
                rows = cursor.fetchall()
                return [
                    Alerta(
                        id=r[0],
                        chat_id=r[1],
                        origem=r[2],
                        destino=r[3],
                        teto=float(r[4]),
                        data_ida=r[5],
                        data_volta=r[6],
                        ultimo_preco=float(r[7]) if r[7] is not None else None,
                        apenas_direto=bool(r[8] == 1),
                        ativo=bool(r[9] == 1),
                        criado_em=str(r[10]) if r[10] else None
                    )
                    for r in rows
                ]
        except Exception as e:
            logging.error(f"Erro ao listar alertas do usuário {chat_id}: {e}")
            return []

    def desativar(self, alerta_id: int, chat_id: int) -> bool:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE alertas SET ativo = 0 WHERE id = ? AND chat_id = ?",
                    (alerta_id, chat_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao desativar alerta #{alerta_id}: {e}")
            return False

    def atualizar_ultimo_preco(self, alerta_id: int, preco: float) -> bool:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE alertas SET ultimo_preco = ? WHERE id = ?",
                    (preco, alerta_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Erro ao atualizar preço do alerta #{alerta_id}: {e}")
            return False

    def listar_alertas_ativos(self, admin_id: int) -> List[Alerta]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.id, a.chat_id, a.origem, a.destino, a.teto, a.data_ida, a.data_volta, a.ultimo_preco, a.apenas_direto, a.ativo, a.criado_em
                    FROM alertas a
                    LEFT JOIN usuarios u ON a.chat_id = u.user_id
                    WHERE a.ativo = 1 AND (u.autorizado = 1 OR a.chat_id = ?)
                """, (admin_id,))
                rows = cursor.fetchall()
                return [
                    Alerta(
                        id=r[0],
                        chat_id=r[1],
                        origem=r[2],
                        destino=r[3],
                        teto=float(r[4]),
                        data_ida=r[5],
                        data_volta=r[6],
                        ultimo_preco=float(r[7]) if r[7] is not None else None,
                        apenas_direto=bool(r[8] == 1),
                        ativo=bool(r[9] == 1),
                        criado_em=str(r[10]) if r[10] else None
                    )
                    for r in rows
                ]
        except Exception as e:
            logging.error(f"Erro ao listar alertas ativos para checagem: {e}")
            return []

    def obter_por_id(self, alerta_id: int) -> Optional[Alerta]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, chat_id, origem, destino, teto, data_ida, data_volta, ultimo_preco, apenas_direto, ativo, criado_em
                    FROM alertas
                    WHERE id = ?
                """, (alerta_id,))
                r = cursor.fetchone()
                if not r:
                    return None
                return Alerta(
                    id=r[0],
                    chat_id=r[1],
                    origem=r[2],
                    destino=r[3],
                    teto=float(r[4]),
                    data_ida=r[5],
                    data_volta=r[6],
                    ultimo_preco=float(r[7]) if r[7] is not None else None,
                    apenas_direto=bool(r[8] == 1),
                    ativo=bool(r[9] == 1),
                    criado_em=str(r[10]) if r[10] else None
                )
        except Exception as e:
            logging.error(f"Erro ao obter alerta #{alerta_id}: {e}")
            return None
