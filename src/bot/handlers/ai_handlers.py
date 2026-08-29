import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.middlewares import requer_autorizacao
from src.services.ai_service import AIService
from src.services.airport_service import AirportService
from src.services.date_service import DateService
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService
from src.models.alerta import Alerta

@requer_autorizacao
async def mensagem_texto_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto:
        return

    config = context.bot_data["config"]
    if not config.gemini_api_key:
        await update.message.reply_text(
            "💡 Para cadastrar um alerta, use:\n"
            "✨ `/novo` - Assistente guiado passo a passo\n"
            "⚡ `/alerta ORIGEM DESTINO TETO DATA_IDA`\n\n"
            "Envie /ajuda para mais opções.",
            parse_mode="Markdown"
        )
        return

    ai_service = context.bot_data.get("ai_service")
    if not ai_service:
        ai_service = AIService(config.gemini_api_key)
        context.bot_data["ai_service"] = ai_service

    # Mostra animação 'digitando...' enquanto o Gemini processa
    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    hoje_iso = DateService.hoje_brasilia().isoformat()
    resultado = ai_service.processar_mensagem(texto, hoje_iso=hoje_iso)

    if not resultado:
        await update.message.reply_text(
            "Desculpe, não consegui entender o pedido no momento. "
            "Você pode tentar reformular ou usar o assistente `/novo`!",
            parse_mode="Markdown"
        )
        return

    # 1. Tratamento de Rate Limit
    if resultado.intencao == "rate_limit":
        await update.message.reply_text(resultado.resposta_direta, parse_mode="Markdown")
        return

    # 2. Resposta de consultor de viagens ou pedido de dado faltante
    if resultado.intencao == "duvida_viagem" or (resultado.resposta_direta and not (resultado.origem and resultado.destino and resultado.teto and resultado.data_ida)):
        await update.message.reply_text(resultado.resposta_direta, parse_mode="Markdown")
        return

    # 3. Processamento de Criação de Alerta
    origem_iata = AirportService.resolver(resultado.origem or "")
    destino_iata = AirportService.resolver(resultado.destino or "")

    if not origem_iata:
        await update.message.reply_text(
            f"🤔 Entendi que a origem é *{resultado.origem}*, mas não encontrei o aeroporto correspondente.\n"
            "Poderia informar a cidade ou sigla (ex: `São Paulo`, `GRU`, `Brasília`)?",
            parse_mode="Markdown"
        )
        return

    if not destino_iata:
        await update.message.reply_text(
            f"🤔 Entendi que o destino é *{resultado.destino}*, mas não encontrei o aeroporto correspondente.\n"
            "Poderia informar a cidade ou sigla (ex: `Miami`, `MIA`, `Lisboa`)?",
            parse_mode="Markdown"
        )
        return

    if origem_iata == destino_iata:
        await update.message.reply_text(
            "⚠️ A origem e o destino não podem ser iguais! Por favor, reformule sua viagem.",
            parse_mode="Markdown"
        )
        return

    data_ida_iso = DateService.parse_data(resultado.data_ida or "")
    if not data_ida_iso:
        await update.message.reply_text(
            "📅 Não consegui identificar a data da viagem.\n"
            "Qual a data de ida desejada? (ex: `15/11/2026` ou `15/11`):",
            parse_mode="Markdown"
        )
        return

    data_volta_iso = DateService.parse_data(resultado.data_volta or "") if resultado.data_volta else None
    teto = resultado.teto

    if not teto or teto <= 0:
        # Salva dados parciais no contexto do usuário e pergunta o teto
        context.user_data["pendente_alerta_ia"] = {
            "origem": origem_iata,
            "destino": destino_iata,
            "data_ida": data_ida_iso,
            "data_volta": data_volta_iso,
        }
        nome_origem = AirportService.nome_formatado(origem_iata)
        nome_destino = AirportService.nome_formatado(destino_iata)
        await update.message.reply_text(
            f"✈️ Entendi a rota: *{nome_origem}* ➔ *{nome_destino}* para {DateService.formatar_br(data_ida_iso)}!\n\n"
            f"💰 *Qual o valor máximo (teto em R$) que você aceita pagar?* (Ex: `800` ou `2500`):",
            parse_mode="Markdown"
        )
        return

    # Guarda o alerta preparado para confirmação
    context.user_data["pendente_alerta_ia"] = {
        "origem": origem_iata,
        "destino": destino_iata,
        "data_ida": data_ida_iso,
        "data_volta": data_volta_iso,
        "teto": float(teto),
    }

    nome_origem = AirportService.nome_formatado(origem_iata)
    nome_destino = AirportService.nome_formatado(destino_iata)
    ida_br = DateService.formatar_br(data_ida_iso)
    volta_br = DateService.formatar_br(data_volta_iso)
    tipo_str = f"Ida ({ida_br}) e Volta ({volta_br})" if data_volta_iso else f"Somente Ida ({ida_br})"

    card_resumo = (
        "🤖 *Entendi seu alerta de voo!*\n\n"
        f"🛫 *Origem:* {nome_origem}\n"
        f"🛬 *Destino:* {nome_destino}\n"
        f"📅 *Datas:* {tipo_str}\n"
        f"💰 *Preço Teto:* R$ {teto:.2f}\n\n"
        "Deseja ativar este monitoramento agora?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar e Ativar", callback_data="ai_confirmar"),
            InlineKeyboardButton("❌ Cancelar", callback_data="ai_cancelar")
        ]
    ]
    await update.message.reply_text(
        card_resumo,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
