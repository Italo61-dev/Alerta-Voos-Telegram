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
        client = genai.Client(
            api_key=config.gemini_api_key,
            http_options=types.HttpOptions(timeout=30000)
        )
        alerta_repo = context.bot_data["alerta_repo"]
        historico_repo = context.bot_data.get("historico_repo")
        agent = TravelAgent(
            client=client,
            user_id=user_id,
            alerta_repo=alerta_repo,
            historico_repo=historico_repo,
            model="gemini-3.5-flash"
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
        "🎙️ _Ouvindo e analisando seu áudio com IA..._",
        parse_mode="Markdown"
    )

    try:
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await tg_file.download_as_bytearray()
        mime_type = voice.mime_type or "audio/ogg"

        user_id = update.effective_user.id
        agent = _obter_ou_criar_agente(context, user_id)

        audio_part = types.Part.from_bytes(data=bytes(audio_bytes), mime_type=mime_type)
        conteudo = [
            audio_part,
            "Ouça com atenção o áudio acima enviado pelo usuário em português. Atenda ao pedido dele sobre passagens aéreas, alertas de preço ou dúvidas de viagem, executando as ferramentas necessárias se ele informou dados de voo."
        ]
        resposta_texto, alerta_id, link_flights = agent.enviar_mensagem(conteudo)

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

        try:
            await update.message.reply_text(resposta_texto, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(resposta_texto, reply_markup=markup)

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
