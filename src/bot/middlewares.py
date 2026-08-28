import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

def requer_autorizacao(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        config = context.bot_data["config"]
        usuario_repo = context.bot_data["usuario_repo"]
        user = update.effective_user
        if not user:
            return

        if user.id == config.admin_id or usuario_repo.is_autorizado(user.id):
            return await func(update, context, *args, **kwargs)

        # Registra solicitação se ainda não constar
        usuario_repo.registrar_solicitacao(
            user_id=user.id,
            nome=user.full_name or "Sem Nome",
            username=user.username or ""
        )

        # Notifica o Administrador no Telegram com botões interativos
        if config.admin_id and user.id != config.admin_id:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user.id}"),
                    InlineKeyboardButton("❌ Recusar", callback_data=f"recusar_{user.id}")
                ]
            ]
            try:
                nome = user.full_name or "Sem nome"
                uname = f"@{user.username}" if user.username else "sem username"
                await context.bot.send_message(
                    chat_id=config.admin_id,
                    text=(
                        f"🔔 *Nova solicitação de acesso!*\n\n"
                        f"👤 *Nome:* {nome}\n"
                        f"🔗 *Username:* {uname}\n"
                        f"🆔 *ID:* `{user.id}`\n\n"
                        f"Deseja autorizar este usuário a monitorar voos?"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            except Exception as ex:
                logging.error(f"Erro ao notificar administrador sobre novo usuário: {ex}")

        if update.message:
            await update.message.reply_text(
                "🔒 *Acesso Restrito*\n\n"
                "Este bot é privado. Uma solicitação de acesso foi enviada ao administrador!\n"
                "Você será avisado aqui assim que o acesso for liberado.",
                parse_mode="Markdown"
            )
    return wrapper

def requer_admin(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        config = context.bot_data["config"]
        user = update.effective_user
        if not user or user.id != config.admin_id:
            if update.message:
                await update.message.reply_text("⛔ Comando restrito ao administrador.", parse_mode="Markdown")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
