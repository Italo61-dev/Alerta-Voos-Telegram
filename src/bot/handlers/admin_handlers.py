import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.middlewares import requer_admin
from src.services.notifier_service import NotifierService

@requer_admin
async def usuarios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_repo = context.bot_data["usuario_repo"]
    config = context.bot_data["config"]
    usuarios = usuario_repo.listar_todos()
    mensagem = NotifierService.mensagem_lista_usuarios(usuarios, config.admin_id)
    await update.message.reply_text(mensagem, parse_mode="Markdown")

@requer_admin
async def aprovar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "⚠️ Informe o ID do usuário. Exemplo: `/aprovar 12345678`",
            parse_mode="Markdown"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ O ID deve ser um número inteiro.",
            parse_mode="Markdown"
        )
        return

    usuario_repo = context.bot_data["usuario_repo"]
    usuario_repo.definir_autorizacao(target_id, True)

    await update.message.reply_text(
        f"✅ Usuário `{target_id}` aprovado com sucesso!",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🎉 *Seu acesso foi liberado pelo administrador!*\n\n"
                "Você já pode cadastrar seus alertas de voos no bot.\n"
                "Envie /ajuda para ver as instruções."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Erro ao notificar usuário aprovado {target_id}: {e}")

@requer_admin
async def bloquear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "⚠️ Informe o ID do usuário. Exemplo: `/bloquear 12345678`",
            parse_mode="Markdown"
        )
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ O ID deve ser um número inteiro.",
            parse_mode="Markdown"
        )
        return

    config = context.bot_data["config"]
    if target_id == config.admin_id:
        await update.message.reply_text(
            "⚠️ Você não pode bloquear o próprio administrador!",
            parse_mode="Markdown"
        )
        return

    usuario_repo = context.bot_data["usuario_repo"]
    usuario_repo.definir_autorizacao(target_id, False)

    await update.message.reply_text(
        f"🚫 Usuário `{target_id}` bloqueado com sucesso!",
        parse_mode="Markdown"
    )
