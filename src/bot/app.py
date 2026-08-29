import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    Application
)
from src.config import Config
from src.database.connection import DatabaseManager
from src.database.usuario_repository import UsuarioRepository
from src.database.alerta_repository import AlertaRepository
from src.database.historico_repository import HistoricoRepository
from src.services.ai_service import AIService
from src.bot.handlers.user_handlers import (
    start_command,
    ajuda_command,
    alerta_command,
    listar_command,
    remover_command,
    testar_command,
)
from src.bot.handlers.admin_handlers import (
    usuarios_command,
    aprovar_command,
    bloquear_command,
)
from src.bot.handlers.callbacks import callback_geral
from src.bot.handlers.wizard_handlers import criar_wizard_handler
from src.bot.handlers.ai_handlers import mensagem_texto_ia, mensagem_audio_ia
from src.bot.scheduler import AlertScheduler

def create_bot_app(config: Config) -> Application:
    db_manager = DatabaseManager(config)
    usuario_repo = UsuarioRepository(db_manager)
    alerta_repo = AlertaRepository(db_manager)
    historico_repo = HistoricoRepository(db_manager)

    async def post_init(application: Application):
        scheduler = AlertScheduler(application.bot, config, alerta_repo, historico_repo)
        asyncio.create_task(scheduler.loop_agendado())

    app = ApplicationBuilder().token(config.telegram_token).post_init(post_init).build()

    # Injeção de dependências no bot_data
    app.bot_data["config"] = config
    app.bot_data["usuario_repo"] = usuario_repo
    app.bot_data["alerta_repo"] = alerta_repo
    app.bot_data["historico_repo"] = historico_repo
    app.bot_data["ai_service"] = AIService(config.gemini_api_key)

    # 1. Wizard Guiado (ConversationHandler)
    app.add_handler(criar_wizard_handler())

    # 2. Handlers de Usuário
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ajuda", ajuda_command))
    app.add_handler(CommandHandler("alerta", alerta_command))
    app.add_handler(CommandHandler("listar", listar_command))
    app.add_handler(CommandHandler("remover", remover_command))
    app.add_handler(CommandHandler("testar", testar_command))

    # 3. Handlers de Administrador
    app.add_handler(CommandHandler("usuarios", usuarios_command))
    app.add_handler(CommandHandler("aprovar", aprovar_command))
    app.add_handler(CommandHandler("bloquear", bloquear_command))

    # 4. Callbacks de Botões Inline Gerais
    app.add_handler(CallbackQueryHandler(callback_geral))

    # 5. Mensagens Livres com IA (Google Gemini) - Texto e Áudio
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_texto_ia))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, mensagem_audio_ia))

    return app
