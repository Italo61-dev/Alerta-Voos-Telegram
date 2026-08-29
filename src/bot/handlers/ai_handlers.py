import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from google import genai
from google.genai import types

from src.bot.middlewares import requer_autorizacao
from src.services.travel_agent import TravelAgent

def _obter_ou_criar_agente(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> TravelAgent:
    agent = context.user_data.get("travel_agent")
    if not agent:
        config = context.bot_data["config"]
        client = genai.Client(api_key=config.gemini_api_key)
        alerta_repo = context.bot_data["alerta_repo"]
        historico_repo = context.bot_data.get("historico_repo")
        agent = TravelAgent(
            client=client,
            user_id=user_id,
            alerta_repo=alerta_repo,
            historico_repo=historico_repo,
            model="gemini-flash-lite-latest",
            max_alertas=config.max_alertas_por_usuario,
            admin_id=config.admin_id
        )
        context.user_data["travel_agent"] = agent
    return agent

@requer_autorizacao
async def mensagem_texto_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto:
        return

    # Comando amigável de limpeza/reset de conversa
    if texto.lower() in ["/reset", "/limpar", "recomeçar", "reiniciar", "limpar conversa"]:
        agent = context.user_data.pop("travel_agent", None)
        if agent:
            agent.reiniciar()
        await update.message.reply_text(
            "🧹 *Conversa reiniciada!* Sobre qual viagem você gostaria de falar agora?",
            parse_mode="Markdown"
        )
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

    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    user_id = update.effective_user.id
    agent = _obter_ou_criar_agente(context, user_id)

    resposta_texto, alerta_id, link_flights = agent.enviar_mensagem(texto)

    # Constrói botões interativos contextuais
    botoes = []
    if link_flights:
        botoes.append([InlineKeyboardButton("🔗 Ver no Google Flights", url=link_flights)])
    if alerta_id:
        botoes.append([InlineKeyboardButton("🗑️ Excluir Alerta", callback_data=f"remover_{alerta_id}")])

    markup = InlineKeyboardMarkup(botoes) if botoes else None

    # Tenta enviar com Markdown; se houver caractere especial sem escape do LLM, envia texto puro
    try:
        await update.message.reply_text(resposta_texto, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(resposta_texto, reply_markup=markup)

@requer_autorizacao
async def mensagem_audio_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = context.bot_data["config"]
    if not config.gemini_api_key:
        await update.message.reply_text(
            "⚠️ O recurso de áudio com IA não está habilitado no momento.",
            parse_mode="Markdown"
        )
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    status_msg = await update.message.reply_text(
        "🎙️ _Ouvindo e transcrevendo seu áudio..._",
        parse_mode="Markdown"
    )

    try:
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await tg_file.download_as_bytearray()
        mime_type = voice.mime_type or "audio/ogg"

        user_id = update.effective_user.id
        agent = _obter_ou_criar_agente(context, user_id)

        # 1. Transcrição rápida e limpa do áudio usando modelo flash-lite (alta cota diária)
        audio_part = types.Part.from_bytes(data=bytes(audio_bytes), mime_type=mime_type)
        client = genai.Client(api_key=config.gemini_api_key)

        transcricao = None
        for mod_tr in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite"]:
            try:
                resp_tr = client.models.generate_content(
                    model=mod_tr,
                    contents=[
                        audio_part,
                        "Você é um transcritor em português. Transcreva fielmente as palavras faladas neste áudio. "
                        "Se for apenas ruído, silêncio ou bipe sem palavras, responda apenas [SEM_FALA]. "
                        "Retorne APENAS o texto falado, sem aspas, sem introduções ou explicações."
                    ],
                    config=types.GenerateContentConfig(
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                )
                if resp_tr.text:
                    texto_candidato = resp_tr.text.strip()
                    if "[SEM_FALA]" not in texto_candidato and len(texto_candidato) > 1:
                        transcricao = texto_candidato
                        break
            except Exception as ex_tr:
                logging.warning(f"Erro na transcrição com {mod_tr}: {ex_tr}")
                continue

        if not transcricao:
            try:
                await status_msg.edit_text(
                    "🎙️ _Não consegui compreender a fala no áudio (parece ter apenas ruído ou silêncio)._\n\n"
                    "Poderia gravar novamente falando mais perto do microfone ou mandar em texto?",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            return

        # Notifica o usuário com a transcrição identificada
        try:
            await status_msg.edit_text(
                f"🎙️ *Você disse:* _\"{transcricao}\"_\n\n"
                f"⏳ _Consultando voos e analisando..._",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # 2. Processa o texto puro no TravelAgent (elimina qualquer erro 400 de áudio em chat histórico)
        resposta_texto, alerta_id, link_flights = agent.enviar_mensagem(transcricao)

        try:
            await status_msg.delete()
        except Exception:
            pass

        botoes = []
        if link_flights:
            botoes.append([InlineKeyboardButton("🔗 Ver no Google Flights", url=link_flights)])
        if alerta_id:
            botoes.append([InlineKeyboardButton("🗑️ Excluir Alerta", callback_data=f"remover_{alerta_id}")])

        markup = InlineKeyboardMarkup(botoes) if botoes else None
        mensagem_final = f"🎙️ *\"_{transcricao}_\"*\n\n{resposta_texto}"

        try:
            await update.message.reply_text(mensagem_final, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(mensagem_final, reply_markup=markup)

    except Exception as e:
        logging.error(f"Erro ao processar áudio via TravelAgent: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            "❌ Ocorreu um erro ao processar seu áudio. Tente enviar em texto!",
            parse_mode="Markdown"
        )
