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
    # 0. Cancelar / Limpar memória
    if resultado.intencao == "cancelar":
        context.user_data.pop("memoria_viagem", None)
        context.user_data.pop("pendente_alerta_ia", None)
        await update.message.reply_text(
            "🧹 *Conversa reiniciada!* Limpei a memória anterior. O que você gostaria de pesquisar ou monitorar agora?",
            parse_mode="Markdown"
        )
        return

    # 1. Tratamento de Rate Limit
    if resultado.intencao == "rate_limit":
        await update.message.reply_text(resultado.resposta_direta or "Limite temporário de IA atingido.", parse_mode="Markdown")
        return

    # 2. Atualiza a memória contínua do usuário no context.user_data
    memoria = context.user_data.get("memoria_viagem", {})
    if resultado.origem:
        memoria["origem"] = resultado.origem
    if resultado.destino:
        memoria["destino"] = resultado.destino
    if resultado.data_ida:
        memoria["data_ida"] = resultado.data_ida
    if resultado.data_volta:
        memoria["data_volta"] = resultado.data_volta
    if resultado.teto:
        memoria["teto"] = resultado.teto
    context.user_data["memoria_viagem"] = memoria

    # 3. Resposta de consultor de viagens (dica de turismo)
    if resultado.intencao == "duvida_viagem":
        await update.message.reply_text(resultado.resposta_direta or "Posso te ajudar com dicas de viagem!", parse_mode="Markdown")
        return

    # Resolve os dados consolidados da memória
    origem_str = memoria.get("origem")
    destino_str = memoria.get("destino")
    data_ida_str = memoria.get("data_ida")
    data_volta_str = memoria.get("data_volta")
    teto_val = memoria.get("teto")

    origem_iata = AirportService.resolver(origem_str or "") if origem_str else None
    destino_iata = AirportService.resolver(destino_str or "") if destino_str else None
    data_ida_iso = DateService.parse_data(data_ida_str or "") if data_ida_str else None
    data_volta_iso = DateService.parse_data(data_volta_str or "") if data_volta_str else None

    # Define se o fluxo é de alerta de preço (se tem teto ou pediu alerta)
    eh_fluxo_alerta = bool(teto_val or resultado.intencao == "criar_alerta")

    # 4. Fluxo de Criação de Alerta de Preço
    if eh_fluxo_alerta:
        # Se ainda faltar algum dado essencial para o alerta (origem, destino, data ou teto)
        if not (origem_iata and destino_iata and data_ida_iso and teto_val):
            await update.message.reply_text(
                resultado.resposta_direta or 
                "Entendido! Para ativar o alerta, qual a data da viagem e o valor máximo (teto em R$) que você quer pagar?",
                parse_mode="Markdown"
            )
            return

        if origem_iata == destino_iata:
            await update.message.reply_text("⚠️ A origem e o destino não podem ser iguais! Digite outro destino:", parse_mode="Markdown")
            return

        status_msg = await update.message.reply_text("🔍 *Analisando seu pedido e verificando preços no Google Flights...*", parse_mode="Markdown")

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

        # Salva o alerta pendente para confirmação
        context.user_data["pendente_alerta_ia"] = {
            "origem": origem_iata,
            "destino": destino_iata,
            "data_ida": data_ida_iso,
            "data_volta": data_volta_iso,
            "teto": float(teto_val),
        }
        # Limpa a memória contínua pois já foi consolidado
        context.user_data.pop("memoria_viagem", None)

        nome_origem = AirportService.nome_formatado(origem_iata)
        nome_destino = AirportService.nome_formatado(destino_iata)
        ida_br = DateService.formatar_br(data_ida_iso)
        volta_br = DateService.formatar_br(data_volta_iso)
        tipo_str = f"Ida ({ida_br}) e Volta ({volta_br})" if data_volta_iso else f"Somente Ida ({ida_br})"

        card_resumo = (
            "🤖 *Entendi seu pedido de alerta!*\n\n"
            f"🛫 *Trecho:* {nome_origem} ➔ {nome_destino}\n"
            f"📅 *Datas:* {tipo_str}\n"
            f"💰 *Preço Teto:* R$ {teto_val:.2f}\n\n"
            f"🔔 *Como funciona:* Eu vou monitorar o Google Flights periodicamente e te aviso assim que encontrar uma passagem por *R$ {teto_val:.2f}* ou menos!\n\n"
        )

        if voos:
            melhor = voos[0]
            if melhor.preco <= teto_val:
                card_resumo += f"🎯 *Preço já bateu a meta agora!* Encontrei voo por *R$ {melhor.preco:.2f}* ({melhor.companhia}), abaixo da sua meta!\n\n"
            else:
                card_resumo += f"📊 *Menor preço agora:* R$ {melhor.preco:.2f} ({melhor.companhia}). Ainda está acima de R$ {teto_val:.2f}, mas vou continuar vigiando!\n\n"

            card_resumo += f"🏆 *Top {min(len(voos), 3)} Melhores Opções Hoje:*\n"
            emojis = ["1️⃣", "2️⃣", "3️⃣"]
            for i, v in enumerate(voos[:3]):
                esc = "Voo direto" if v.escalas == 0 else f"{v.escalas} conexão(ões)"
                card_resumo += f"{emojis[i]} *R$ {v.preco:.2f}* — {v.companhia} ({esc})\n"
            card_resumo += "\n"

        card_resumo += "Está tudo certo para ativar este monitoramento?"

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar e Ativar Alerta", callback_data="ai_confirmar")],
            [InlineKeyboardButton("🔗 Ver no Google Flights", url=link)],
            [InlineKeyboardButton("❌ Cancelar", callback_data="ai_cancelar")]
        ]
        await update.message.reply_text(card_resumo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # 5. Pesquisa Instantânea de Voos (quando não especificou teto e pediu apenas cotação)
    if resultado.intencao == "pesquisar_voos":
        if not (origem_iata and destino_iata and data_ida_iso):
            await update.message.reply_text(
                resultado.resposta_direta or 
                "🤔 Para pesquisar os voos, informe a cidade de origem, destino e data! (Ex: 'Saindo de SP dia 15/11')",
                parse_mode="Markdown"
            )
            return

        if origem_iata == destino_iata:
            await update.message.reply_text("⚠️ A origem e o destino não podem ser iguais!", parse_mode="Markdown")
            return

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

        melhor_preco = voos[0].preco if voos else 1000.0
        context.user_data["pendente_alerta_ia"] = {
            "origem": origem_iata,
            "destino": destino_iata,
            "data_ida": data_ida_iso,
            "data_volta": data_volta_iso,
            "teto": float(melhor_preco),
        }
        context.user_data.pop("memoria_viagem", None)

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

    # 6. Fallback de conversa direta
    await update.message.reply_text(
        resultado.resposta_direta or "Como posso te ajudar com sua viagem? Diga para onde quer ir e quando!",
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

    # Animação 'digitando...'
    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    hoje_iso = DateService.hoje_brasilia().isoformat()
    memoria_anterior = context.user_data.get("memoria_viagem", {})
    resultado = ai_service.processar_mensagem(texto, hoje_iso=hoje_iso, memoria_anterior=memoria_anterior)

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
        memoria_anterior = context.user_data.get("memoria_viagem", {})
        resultado = ai_service.processar_audio(
            bytes(audio_bytes),
            mime_type=mime_type,
            hoje_iso=hoje_iso,
            memoria_anterior=memoria_anterior
        )

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
