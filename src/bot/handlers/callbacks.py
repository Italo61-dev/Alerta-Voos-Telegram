import logging
from telegram import Update
from telegram.ext import ContextTypes

async def callback_aprovacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    config = context.bot_data["config"]
    usuario_repo = context.bot_data["usuario_repo"]
    user_id = update.effective_user.id

    if user_id != config.admin_id:
        await query.edit_message_text("⛔ Ação permitida apenas para o administrador.")
        return

    data = query.data
    if data.startswith("aprovar_"):
        try:
            target_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return

        usuario_repo.definir_autorizacao(target_id, True)
        await query.edit_message_text(
            f"✅ Usuário `{target_id}` *aprovado com sucesso!*",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎉 *Seu acesso foi aprovado pelo administrador!*\n\n"
                    "Agora você já pode monitorar passagens aéreas.\n"
                    "Envie /start ou /ajuda para ver as instruções."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Erro ao notificar usuário {target_id} após aprovação via callback: {e}")

    elif data.startswith("recusar_"):
        try:
            target_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return

        usuario_repo.definir_autorizacao(target_id, False)
        await query.edit_message_text(
            f"❌ Usuário `{target_id}` *recusado/bloqueado.*",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="🚫 Sua solicitação de acesso não foi aprovada pelo administrador.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Erro ao notificar usuário {target_id} após recusa via callback: {e}")
