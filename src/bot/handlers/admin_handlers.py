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

@requer_admin
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_comando = update.message.text or ""
    partes = texto_comando.split(maxsplit=1)

    if len(partes) < 2 or not partes[1].strip():
        await update.message.reply_text(
            "📢 *Como usar a Transmissão em Massa:*\n\n"
            "• `/broadcast <sua mensagem>` — Envia uma mensagem personalizada para todos os usuários autorizados.\n"
            "_Exemplo:_ `/broadcast 🔥 MEGA PROMOÇÃO! Voos SP -> Salvador por R$ 250 ida e volta!`\n\n"
            "• `/broadcast_novidades` — Dispara automaticamente o resumo oficial com todas as novidades do bot e instruções práticas de como usar cada funcionalidade (sem precisar digitar nada!).",
            parse_mode="Markdown"
        )
        return

    mensagem_envio = partes[1].strip()
    status_msg = await update.message.reply_text(
        "⏳ *Iniciando transmissão global para todos os usuários autorizados...*",
        parse_mode="Markdown"
    )

    from src.services.broadcast_service import BroadcastService
    usuario_repo = context.bot_data["usuario_repo"]
    destinatarios = usuario_repo.listar_autorizados()

    if not destinatarios:
        await status_msg.edit_text("⚠️ Nenhum usuário autorizado encontrado para envio.")
        return

    resultado = await BroadcastService.enviar_broadcast(
        bot=context.bot,
        destinatarios=destinatarios,
        mensagem=f"📢 *COMUNICADO DO ADMINISTRADOR*\n\n{mensagem_envio}"
    )

    await status_msg.edit_text(
        f"📢 *Transmissão Concluída!*\n\n"
        f"👥 *Total de destinatários:* {resultado['total']}\n"
        f"✅ *Enviados com sucesso:* {resultado['sucessos']}\n"
        f"❌ *Falhas na entrega:* {resultado['falhas']}",
        parse_mode="Markdown"
    )

@requer_admin
async def broadcast_novidades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text(
        "⏳ *Disparando comunicado oficial de novidades para todos os usuários autorizados...*",
        parse_mode="Markdown"
    )

    from src.services.broadcast_service import BroadcastService
    usuario_repo = context.bot_data["usuario_repo"]
    destinatarios = usuario_repo.listar_autorizados()

    if not destinatarios:
        await status_msg.edit_text("⚠️ Nenhum usuário autorizado encontrado para envio.")
        return

    mensagem_novidades = BroadcastService.formatar_mensagem_novidades()
    resultado = await BroadcastService.enviar_broadcast(
        bot=context.bot,
        destinatarios=destinatarios,
        mensagem=mensagem_novidades
    )

    await status_msg.edit_text(
        f"🚀 *Novidades Transmitidas com Sucesso!*\n\n"
        f"👥 *Total de destinatários:* {resultado['total']}\n"
        f"✅ *Enviados com sucesso:* {resultado['sucessos']}\n"
        f"❌ *Falhas na entrega:* {resultado['falhas']}",
        parse_mode="Markdown"
    )
