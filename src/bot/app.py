import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    Application
)
from src.config import Config
from src.database.connection import DatabaseManager
from src.database.usuario_repository import UsuarioRepository
from src.database.alerta_repository import AlertaRepository
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
from src.bot.handlers.callbacks import callback_aprovacao
from src.bot.scheduler import AlertScheduler

def create_bot_app(config: Config) -> Application:
    db_manager = DatabaseManager(config)
    usuario_repo = UsuarioRepository(db_manager)
    alerta_repo = AlertaRepository(db_manager)

    async def post_init(application: Application):
        scheduler = AlertScheduler(application.bot, config, alerta_repo)
        asyncio.create_task(scheduler.loop_agendado())

    app = ApplicationBuilder().token(config.telegram_token).post_init(post_init).build()

    # Injeção de dependências no bot_data
    app.bot_data["config"] = config
    app.bot_data["usuario_repo"] = usuario_repo
    app.bot_data["alerta_repo"] = alerta_repo

    # Handlers de Usuário
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ajuda", ajuda_command))
    app.add_handler(CommandHandler("alerta", alerta_command))
    app.add_handler(CommandHandler("listar", listar_command))
    app.add_handler(CommandHandler("remover", remover_command))
    app.add_handler(CommandHandler("testar", testar_command))

    # Handlers de Administrador
    app.add_handler(CommandHandler("usuarios", usuarios_command))
    app.add_handler(CommandHandler("aprovar", aprovar_command))
    app.add_handler(CommandHandler("bloquear", bloquear_command))

    # Callbacks de Botões Inline
    app.add_handler(CallbackQueryHandler(callback_aprovacao))

    return app
