import logging
from src.config import load_config
from src.database.schema import init_db
from src.bot.server import HealthCheckServer
from src.bot.app import create_bot_app

def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    # Silencia logs barulhentos de polling do httpx e avisos internos do SDK google_genai
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)
    logging.getLogger("google_genai.models").setLevel(logging.ERROR)

    config = load_config()
    logging.info(f"Iniciando Bot de Alerta de Passagens (Admin ID: {config.admin_id})...")

    # Inicializa tabelas e admin padrão no banco (Turso ou SQLite local)
    init_db(config)

    # Inicia servidor HTTP para compatibilidade com plataformas de nuvem (Render/Heroku)
    server = HealthCheckServer(port=config.port)
    server.start()

    # Cria e executa o bot do Telegram
    app = create_bot_app(config)
    logging.info("🤖 Bot inicializado com sucesso e escutando requisições no Telegram!")
    app.run_polling()

if __name__ == "__main__":
    main()
