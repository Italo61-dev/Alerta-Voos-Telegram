import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.middlewares import requer_autorizacao
from src.services.ai_service import AIService, DadosAlertaIA
from src.services.airport_service import AirportService
from src.services.date_service import DateService
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService

async def _processar_resultado_ia(update: Update, context: ContextTypes.DEFAULT_TYPE, resultado: DadosAlertaIA):
    # 1. Tratamento de Rate Limit
    if resultado.intencao == "rate_limit":
        await update.message.reply_text(resultado.resposta_direta or "Limite atingido.", parse_mode="Markdown")
        return

    # 2. Resposta de consultor de viagens
    if resultado.intencao == "duvida_viagem":
        await update.message.reply_text(resultado.resposta_direta or "Posso te ajudar com dúvidas de viagem!", parse_mode="Markdown")
        return

    # 3. Pesquisa Instantânea de Voos (Top 3 Melhores Opções)
    if resultado.intencao == "pesquisar_voos":
        origem_iata = AirportService.resolver(resultado.origem or "")
        destino_iata = AirportService.resolver(resultado.destino or "")

        if not origem_iata or not destino_iata:
            await update.message.reply_text(
                resultado.resposta_direta or 
                "🤔 Para pesquisar os voos, informe a cidade de origem e destino! (Ex: 'Voos de SP pra Salvador dia 15/11')",
                parse_mode="Markdown"
            )
            return

        if origem_iata == destino_iata:
            await update.message.reply_text("⚠️ A origem e o destino não podem ser iguais!", parse_mode="Markdown")
            return

        data_ida_iso = DateService.parse_data(resultado.data_ida or "")
        if not data_ida_iso:
            await update.message.reply_text(
                "📅 Para qual data você gostaria de pesquisar esses voos? (Ex: `15/11/2026` ou `15/11`):",
                parse_mode="Markdown"
            )
            return

        data_volta_iso = DateService.parse_data(resultado.data_volta or "") if resultado.data_volta else None

        status_msg = await update.message.reply_text("🔍 *Consultando o Google Flights em tempo real...*", parse_mode="Markdown")

        voos = FlightService.buscar_voos(
            origem=origem_iata,
            destino=destino_iata,
            data_ida=data_ida_iso,
            data_volta=data_volta_iso
        )

        link = FlightService.gerar_link_google_flights(
            origem=origem_iata,
            destino=destino_iata,
            data_ida=data_ida_iso,
            data_volta=data_volta_iso
        )

        try:
            await status_msg.delete()
        except Exception:
            pass

        # Salva o trecho pesquisado em context.user_data caso o usuário queira criar alerta pelo botão
        melhor_preco = voos[0].preco if voos else (resultado.teto or 1000.0)
        context.user_data["pendente_alerta_ia"] = {
            "origem": origem_iata,
            "destino": destino_iata,
            "data_ida": data_ida_iso,
            "data_volta": data_volta_iso,
            "teto": float(melhor_preco),
        }

        texto_resultado = NotifierService.mensagem_resultado_busca(
            origem=origem_iata,
            destino=destino_iata,
            data_ida=data_ida_iso,
            data_volta=data_volta_iso,
            voos=voos
        )
        botoes = NotifierService.botoes_resultado_busca(link)
        await update.message.reply_text(texto_resultado, reply_markup=botoes, parse_mode="Markdown")
        return

    # 4. Se faltar dados fundamentais para criar alerta
    if resultado.resposta_direta and not (resultado.origem and resultado.destino and resultado.teto and resultado.data_ida):
        await update.message.reply_text(resultado.resposta_direta, parse_mode="Markdown")
        return

    # 5. Processamento de Criação de Alerta
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
        "🤖 *Entendi seu pedido de alerta!*\n\n"
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

    await _processar_resultado_ia(update, context, resultado)

@requer_autorizacao
async def mensagem_audio_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = context.bot_data["config"]
    if not config.gemini_api_key:
        await update.message.reply_text(
            "⚠️ O recurso de áudio com IA não está habilitado no momento.",
            parse_mode="Markdown"
        )
        return

    ai_service = context.bot_data.get("ai_service")
    if not ai_service:
        ai_service = AIService(config.gemini_api_key)
        context.bot_data["ai_service"] = ai_service

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    status_msg = await update.message.reply_text(
        "🎙️ _Ouvindo e analisando seu áudio com IA..._",
        parse_mode="Markdown"
    )

    try:
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await tg_file.download_as_bytearray()
        mime_type = voice.mime_type or "audio/ogg"

        hoje_iso = DateService.hoje_brasilia().isoformat()
        resultado = ai_service.processar_audio(bytes(audio_bytes), mime_type=mime_type, hoje_iso=hoje_iso)

        try:
            await status_msg.delete()
        except Exception:
            pass

        if not resultado:
            await update.message.reply_text(
                "❌ Não consegui compreender o áudio. Tente enviar novamente falando mais perto do microfone ou digite em texto!",
                parse_mode="Markdown"
            )
            return

        await _processar_resultado_ia(update, context, resultado)
    except Exception as e:
        logging.error(f"Erro ao processar áudio via IA: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro ao processar seu áudio. Tente enviar em texto!",
            parse_mode="Markdown"
        )
