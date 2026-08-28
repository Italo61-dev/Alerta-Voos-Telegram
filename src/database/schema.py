import logging
from src.config import Config
from src.database.connection import DatabaseManager

def init_db(config: Config):
    db_manager = DatabaseManager(config)
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                origem TEXT NOT NULL,
                destino TEXT NOT NULL,
                teto REAL NOT NULL,
                data_ida TEXT NOT NULL,
                data_volta TEXT,
                ultimo_preco REAL,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                nome TEXT,
                username TEXT,
                autorizado INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        if config.admin_id:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO usuarios (user_id, nome, username, autorizado)
                    VALUES (?, 'Administrador', 'admin', 1)
                """, (config.admin_id,))
                cursor.execute(
                    "UPDATE usuarios SET autorizado = 1 WHERE user_id = ?",
                    (config.admin_id,)
                )
            except Exception as e:
                logging.error(f"Erro ao registrar admin padrão: {e}")
    logging.info("Tabelas do banco de dados inicializadas com sucesso.")
