import warnings
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.warnings import PTBUserWarning
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

warnings.filterwarnings("ignore", category=PTBUserWarning)

from src.bot.middlewares import requer_autorizacao
from src.services.airport_service import AirportService
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService
from src.models.alerta import Alerta

# Estados da conversação
ESCOLHER_ORIGEM = 1
ESCOLHER_DESTINO = 2
ESCOLHER_TIPO = 3
ESCOLHER_DATA_IDA = 4
ESCOLHER_DATA_VOLTA = 5
ESCOLHER_TETO = 6
CONFIRMAR_ALERTA = 7

@requer_autorizacao
async def iniciar_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["novo_alerta"] = {}
    await update.message.reply_text(
        "✈️ *Assistente de Criação de Alerta*\n\n"
        "Vamos configurar seu alerta em poucos passos!\n"
        "_(A qualquer momento você pode digitar /cancelar)_\n\n"
        "🛫 *Passo 1 de 5:* De qual cidade ou aeroporto você vai sair?\n"
        "_(Ex: São Paulo, Rio, Brasília, GRU, BSB)_",
        parse_mode="Markdown"
    )
    return ESCOLHER_ORIGEM

async def receber_origem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    iata = AirportService.resolver(texto)

    if not iata:
        await update.message.reply_text(
            f"❌ Não reconheci a cidade ou aeroporto `{texto}`.\n"
            "Tente digitar a sigla (ex: `GRU`, `BSB`, `GIG`) ou o nome da cidade (ex: `São Paulo`, `Brasília`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_ORIGEM

    context.user_data["novo_alerta"]["origem"] = iata
    nome_origem = AirportService.nome_formatado(iata)

    await update.message.reply_text(
        f"✅ *Origem definida:* {nome_origem}\n\n"
        f"🛬 *Passo 2 de 5:* Para qual cidade ou aeroporto você quer ir?\n"
        f"_(Ex: Miami, Lisboa, Orlando, Paris, Natal, Salvador)_",
        parse_mode="Markdown"
    )
    return ESCOLHER_DESTINO

async def receber_destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    iata = AirportService.resolver(texto)

    if not iata:
        await update.message.reply_text(
            f"❌ Não reconheci a cidade ou aeroporto `{texto}`.\n"
            "Tente digitar a sigla (ex: `MIA`, `LIS`, `NAT`) ou o nome da cidade (ex: `Miami`, `Lisboa`, `Salvador`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DESTINO

    origem = context.user_data["novo_alerta"]["origem"]
    if iata == origem:
        await update.message.reply_text(
            "⚠️ O destino não pode ser igual à origem! Digite outro destino:",
            parse_mode="Markdown"
        )
        return ESCOLHER_DESTINO

    context.user_data["novo_alerta"]["destino"] = iata
    nome_destino = AirportService.nome_formatado(iata)

    keyboard = [
        [
            InlineKeyboardButton("➡️ Somente Ida", callback_data="tipo_ida"),
            InlineKeyboardButton("🔁 Ida e Volta", callback_data="tipo_ida_volta")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ *Destino definido:* {nome_destino}\n\n"
        f"✈️ *Passo 3 de 5:* Qual o tipo da viagem?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ESCOLHER_TIPO

async def receber_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tipo = query.data
    context.user_data["novo_alerta"]["tipo"] = tipo

    if tipo == "tipo_ida":
        await query.edit_message_text(
            "📅 *Passo 4 de 5:* Qual a data do voo?\n"
            "Use o formato `AAAA-MM-DD` (ex: `2026-11-15`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DATA_IDA
    else:
        await query.edit_message_text(
            "📅 *Passo 4 de 5:* Qual a *Data de Ida*?\n"
            "Use o formato `AAAA-MM-DD` (ex: `2026-11-10`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DATA_IDA

async def receber_data_ida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        dt = datetime.strptime(texto, "%Y-%m-%d")
        if dt.date() < datetime.now().date():
            await update.message.reply_text(
                "❌ A data de ida não pode ser no passado! Digite uma data futura (ex: `2026-11-15`):",
                parse_mode="Markdown"
            )
            return ESCOLHER_DATA_IDA
    except ValueError:
        await update.message.reply_text(
            "❌ Formato inválido! Use `AAAA-MM-DD` (ex: `2026-11-15`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DATA_IDA

    context.user_data["novo_alerta"]["data_ida"] = texto

    if context.user_data["novo_alerta"].get("tipo") == "tipo_ida_volta":
        await update.message.reply_text(
            f"✅ *Data de Ida:* {texto}\n\n"
            f"📅 Agora digite a *Data de Volta* (formato `AAAA-MM-DD`, ex: `2026-11-20`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DATA_VOLTA
    else:
        context.user_data["novo_alerta"]["data_volta"] = None
        await update.message.reply_text(
            f"✅ *Data de Ida:* {texto}\n\n"
            f"💰 *Passo 5 de 5:* Qual o valor máximo (teto) em R$ que você aceita pagar?\n"
            f"_(Digite apenas o número, ex: `500` ou `2500`)_",
            parse_mode="Markdown"
        )
        return ESCOLHER_TETO

async def receber_data_volta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    data_ida = context.user_data["novo_alerta"]["data_ida"]
    try:
        dt_volta = datetime.strptime(texto, "%Y-%m-%d")
        dt_ida = datetime.strptime(data_ida, "%Y-%m-%d")
        if dt_volta < dt_ida:
            await update.message.reply_text(
                "❌ A data de volta não pode ser anterior à data de ida! Digite novamente:",
                parse_mode="Markdown"
            )
            return ESCOLHER_DATA_VOLTA
    except ValueError:
        await update.message.reply_text(
            "❌ Formato inválido! Use `AAAA-MM-DD` (ex: `2026-11-20`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_DATA_VOLTA

    context.user_data["novo_alerta"]["data_volta"] = texto

    await update.message.reply_text(
        f"✅ *Data de Volta:* {texto}\n\n"
        f"💰 *Passo 5 de 5:* Qual o valor máximo (teto) em R$ que você aceita pagar pela viagem completa?\n"
        f"_(Digite apenas o número, ex: `800` ou `4200`)_",
        parse_mode="Markdown"
    )
    return ESCOLHER_TETO

async def receber_teto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().replace("R$", "").replace(",", ".")
    try:
        teto = float(texto)
        if teto <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ Digite um valor numérico positivo (ex: `500` ou `2500`):",
            parse_mode="Markdown"
        )
        return ESCOLHER_TETO

    dados = context.user_data["novo_alerta"]
    dados["teto"] = teto

    origem = dados["origem"]
    destino = dados["destino"]
    data_ida = dados["data_ida"]
    data_volta = dados["data_volta"]

    nome_origem = AirportService.nome_formatado(origem)
    nome_destino = AirportService.nome_formatado(destino)
    tipo_str = f"Ida ({data_ida}) e Volta ({data_volta})" if data_volta else f"Somente Ida ({data_ida})"

    resumo = (
        "🎯 *Confirmação do Alerta de Preço:*\n\n"
        f"🛫 *Origem:* {nome_origem}\n"
        f"🛬 *Destino:* {nome_destino}\n"
        f"📅 *Datas:* {tipo_str}\n"
        f"💰 *Preço Teto:* R$ {teto:.2f}\n\n"
        "Deseja ativar este monitoramento agora?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar e Ativar", callback_data="confirmar_wizard_sim"),
            InlineKeyboardButton("❌ Cancelar", callback_data="confirmar_wizard_nao")
        ]
    ]
    await update.message.reply_text(
        resumo,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CONFIRMAR_ALERTA

async def confirmar_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirmar_wizard_sim":
        dados = context.user_data.get("novo_alerta", {})
        if not dados:
            await query.edit_message_text("⚠️ Dados da criação expiraram. Inicie novamente com /novo.")
            return ConversationHandler.END

        chat_id = update.effective_chat.id
        alerta_repo = context.bot_data["alerta_repo"]

        novo_alerta = Alerta(
            id=None,
            chat_id=chat_id,
            origem=dados["origem"],
            destino=dados["destino"],
            teto=dados["teto"],
            data_ida=dados["data_ida"],
            data_volta=dados.get("data_volta")
        )
        alerta_id = alerta_repo.salvar(novo_alerta)
        novo_alerta.id = alerta_id

        link = FlightService.gerar_link_google_flights(
            dados["origem"], dados["destino"], dados["data_ida"], dados.get("data_volta")
        )
        botoes = NotifierService.botoes_card_alerta(novo_alerta, link)
        resposta = NotifierService.mensagem_alerta_cadastrado(alerta_id, novo_alerta)

        await query.edit_message_text(resposta, reply_markup=botoes, parse_mode="Markdown")
        context.user_data.pop("novo_alerta", None)
        return ConversationHandler.END

    else:
        await query.edit_message_text("❌ Criação de alerta cancelada.")
        context.user_data.pop("novo_alerta", None)
        return ConversationHandler.END

async def cancelar_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("novo_alerta", None)
    await update.message.reply_text(
        "❌ Criação de alerta cancelada. Quando quiser, basta digitar /novo ou /alerta!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

def criar_wizard_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("novo", iniciar_wizard),
        ],
        states={
            ESCOLHER_ORIGEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_origem)],
            ESCOLHER_DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_destino)],
            ESCOLHER_TIPO: [CallbackQueryHandler(receber_tipo, pattern="^tipo_")],
            ESCOLHER_DATA_IDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data_ida)],
            ESCOLHER_DATA_VOLTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data_volta)],
            ESCOLHER_TETO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_teto)],
            CONFIRMAR_ALERTA: [CallbackQueryHandler(confirmar_alerta, pattern="^confirmar_wizard_")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_wizard)],
        per_chat=True,
    )
