import logging
from typing import List, Optional
from src.database.connection import DatabaseManager
from src.models.historico import RegistroHistorico, EstatisticasTrecho

class HistoricoRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def registrar(
        self,
        origem: str,
        destino: str,
        data_ida: str,
        preco: float,
        companhia: str = "",
        escalas: int = 0,
        data_volta: Optional[str] = None,
        alerta_id: Optional[int] = None
    ) -> int:
        """Registra uma cotação de preço no histórico."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO historico_precos 
                    (alerta_id, origem, destino, data_ida, data_volta, preco, companhia, escalas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alerta_id,
                    origem.upper(),
                    destino.upper(),
                    data_ida,
                    data_volta,
                    float(preco),
                    companhia,
                    int(escalas)
                ))
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Erro ao registrar histórico {origem}->{destino}: {e}")
            return -1

    def obter_estatisticas(
        self,
        origem: str,
        destino: str,
        data_ida: Optional[str] = None
    ) -> EstatisticasTrecho:
        """
        Calcula estatísticas de preço (menor, maior, média e última cotação)
        para um trecho específico ou rota geral.
        """
        origem_u = origem.upper()
        destino_u = destino.upper()

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                if data_ida:
                    cursor.execute("""
                        SELECT 
                            COUNT(*),
                            MIN(preco),
                            MAX(preco),
                            AVG(preco)
                        FROM historico_precos
                        WHERE origem = ? AND destino = ? AND data_ida = ?
                    """, (origem_u, destino_u, data_ida))
                else:
                    cursor.execute("""
                        SELECT 
                            COUNT(*),
                            MIN(preco),
                            MAX(preco),
                            AVG(preco)
                        FROM historico_precos
                        WHERE origem = ? AND destino = ?
                    """, (origem_u, destino_u))

                row = cursor.fetchone()
                total = row[0] if row else 0

                if not total or row[1] is None:
                    return EstatisticasTrecho(
                        origem=origem_u,
                        destino=destino_u,
                        total_registros=0
                    )

                menor = float(row[1])
                maior = float(row[2])
                medio = float(row[3])

                # Busca último preço e companhia mais frequente nas menores cotações
                cursor.execute("""
                    SELECT preco, companhia 
                    FROM historico_precos
                    WHERE origem = ? AND destino = ?
                    ORDER BY id DESC LIMIT 1
                """, (origem_u, destino_u))
                ultimo_row = cursor.fetchone()
                ultimo = float(ultimo_row[0]) if ultimo_row else None

                cursor.execute("""
                    SELECT companhia, COUNT(*) as qtd
                    FROM historico_precos
                    WHERE origem = ? AND destino = ? AND preco = ?
                    GROUP BY companhia
                    ORDER BY qtd DESC LIMIT 1
                """, (origem_u, destino_u, menor))
                cia_row = cursor.fetchone()
                melhor_cia = cia_row[0] if cia_row else None

                return EstatisticasTrecho(
                    origem=origem_u,
                    destino=destino_u,
                    total_registros=total,
                    menor_preco=menor,
                    maior_preco=maior,
                    preco_medio=medio,
                    ultimo_preco=ultimo,
                    companhia_mais_barata=melhor_cia
                )
        except Exception as e:
            logging.error(f"Erro ao obter estatísticas de {origem}->{destino}: {e}")
            return EstatisticasTrecho(origem=origem_u, destino=destino_u, total_registros=0)

    def listar_por_alerta(self, alerta_id: int, limite: int = 15) -> List[RegistroHistorico]:
        """Lista os registros de histórico vinculados a um alerta."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, alerta_id, origem, destino, data_ida, data_volta, preco, companhia, escalas, consultado_em
                    FROM historico_precos
                    WHERE alerta_id = ?
                    ORDER BY id DESC LIMIT ?
                """, (alerta_id, limite))
                rows = cursor.fetchall()
                return [
                    RegistroHistorico(
                        id=r[0],
                        alerta_id=r[1],
                        origem=r[2],
                        destino=r[3],
                        data_ida=r[4],
                        data_volta=r[5],
                        preco=float(r[6]),
                        companhia=r[7],
                        escalas=r[8],
                        consultado_em=str(r[9]) if r[9] else None
                    )
                    for r in rows
                ]
        except Exception as e:
            logging.error(f"Erro ao listar histórico do alerta {alerta_id}: {e}")
            return []

    def obter_metricas(self) -> dict:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM historico_precos")
                row = cursor.fetchone()
                total_cotacoes = row[0] if row else 0

                cursor.execute("SELECT COUNT(DISTINCT origem || '-' || destino) FROM historico_precos")
                row_dist = cursor.fetchone()
                trechos_unicos = row_dist[0] if row_dist else 0

                return {
                    "total_cotacoes": total_cotacoes,
                    "trechos_unicos": trechos_unicos
                }
        except Exception as e:
            logging.error(f"Erro ao obter métricas de histórico: {e}")
            return {"total_cotacoes": 0, "trechos_unicos": 0}
