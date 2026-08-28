from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.middlewares import requer_autorizacao
from src.models.alerta import Alerta
from src.services.notifier_service import NotifierService
from src.bot.scheduler import AlertScheduler

@requer_autorizacao
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = context.bot_data["config"]
    is_admin = update.effective_user.id == config.admin_id
    mensagem = NotifierService.mensagem_boas_vindas(is_admin=is_admin)
    await update.message.reply_text(mensagem, parse_mode="Markdown")

@requer_autorizacao
async def ajuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

@requer_autorizacao
async def alerta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args or []

    if len(args) < 4:
        await update.message.reply_text(
            "⚠️ *Parâmetros insuficientes!*\n\n"
            "Use o formato:\n"
            "`/alerta ORIGEM DESTINO VALOR_TETO AAAA-MM-DD [AAAA-MM-DD]`\n\n"
            "*Exemplo:* `/alerta BSB NAT 500 2026-10-15`",
            parse_mode="Markdown"
        )
        return

    origem = args[0].upper().strip()
    destino = args[1].upper().strip()

    try:
        teto = float(args[2].replace("R$", "").replace(",", ".").strip())
        if teto <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ *Valor teto inválido!* Digite um número positivo (ex: `500` ou `450.50`).",
            parse_mode="Markdown"
        )
        return

    data_ida = args[3].strip()
    data_volta = args[4].strip() if len(args) > 4 else None

    try:
        dt_ida = datetime.strptime(data_ida, "%Y-%m-%d")
        if data_volta:
            dt_volta = datetime.strptime(data_volta, "%Y-%m-%d")
            if dt_volta < dt_ida:
                await update.message.reply_text(
                    "❌ *A data de volta não pode ser anterior à data de ida!*",
                    parse_mode="Markdown"
                )
                return
    except ValueError:
        await update.message.reply_text(
            "❌ *Formato de data inválido!* Use o formato `AAAA-MM-DD` (ex: `2026-10-15`).",
            parse_mode="Markdown"
        )
        return

    alerta_repo = context.bot_data["alerta_repo"]
    novo_alerta = Alerta(
        id=None,
        chat_id=chat_id,
        origem=origem,
        destino=destino,
        teto=teto,
        data_ida=data_ida,
        data_volta=data_volta
    )
    alerta_id = alerta_repo.salvar(novo_alerta)
    novo_alerta.id = alerta_id

    resposta = NotifierService.mensagem_alerta_cadastrado(alerta_id, novo_alerta)
    await update.message.reply_text(resposta, parse_mode="Markdown")

@requer_autorizacao
async def listar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    alerta_repo = context.bot_data["alerta_repo"]
    alertas = alerta_repo.listar_por_usuario(chat_id)
    resposta = NotifierService.mensagem_lista_alertas(alertas)
    await update.message.reply_text(resposta, parse_mode="Markdown")

@requer_autorizacao
async def remover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "⚠️ Informe o ID do alerta. Exemplo: `/remover 1`",
            parse_mode="Markdown"
        )
        return

    try:
        alerta_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ O ID deve ser um número inteiro.",
            parse_mode="Markdown"
        )
        return

    alerta_repo = context.bot_data["alerta_repo"]
    sucesso = alerta_repo.desativar(alerta_id, chat_id)

    if sucesso:
        await update.message.reply_text(
            f"🗑️ *Alerta #{alerta_id} removido com sucesso!*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❓ Alerta #{alerta_id} não encontrado ou já removido.",
            parse_mode="Markdown"
        )

@requer_autorizacao
async def testar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *Consultando o Google Flights agora...*",
        parse_mode="Markdown"
    )
    config = context.bot_data["config"]
    alerta_repo = context.bot_data["alerta_repo"]
    scheduler = AlertScheduler(context.bot, config, alerta_repo)
    notificados = await scheduler.verificar_alertas()

    await update.message.reply_text(
        f"✔️ *Consulta finalizada!* {notificados} notificação(ões) enviada(s).",
        parse_mode="Markdown"
    )
