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
                apenas_direto INTEGER DEFAULT 0,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alerta_id INTEGER,
                origem TEXT NOT NULL,
                destino TEXT NOT NULL,
                data_ida TEXT NOT NULL,
                data_volta TEXT,
                preco REAL NOT NULL,
                companhia TEXT,
                escalas INTEGER DEFAULT 0,
                consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alerta_id) REFERENCES alertas(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_historico_trecho 
            ON historico_precos (origem, destino, data_ida)
        """)

        # Migração segura para bancos pré-existentes
        try:
            cursor.execute("ALTER TABLE alertas ADD COLUMN apenas_direto INTEGER DEFAULT 0")
        except Exception:
            pass
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
