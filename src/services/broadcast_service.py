import asyncio
import logging
from typing import List, Dict
from telegram import Bot
from telegram.error import TelegramError
from src.models.usuario import Usuario

class BroadcastService:
    @staticmethod
    def formatar_mensagem_novidades() -> str:
        return (
            "🚀 *NOVIDADES NO BOT DE VOOS! O QUE MUDOU?*\n\n"
            "Preparamos uma série de novas funcionalidades para deixar sua busca de passagens aéreas muito mais rápida, inteligente e prática. Veja o que mudou e como usar:\n\n"
            "🎙️ *1. Áudios de Voz com IA*\n"
            "• *O que mudou:* Agora você não precisa digitar! O bot processa mensagens de voz diretamente.\n"
            "• *Como usar:* Segure o microfone e mande um áudio dizendo por exemplo: _\"Quero ir de São Paulo para Natal em novembro por até 800 reais\"_.\n\n"
            "🧠 *2. Consultor Inteligente & Top 3 Menores Preços*\n"
            "• *O que mudou:* O cérebro do Google Gemini pesquisa o Google Flights em tempo real e responde dúvidas de viagem.\n"
            "• *Como usar:* Pergunte no chat: _\"Quais os 3 voos mais baratos para Salvador no mês que vem?\"_ ou _\"Dicas de turismo em Gramado\"_.\n\n"
            "🔥 *3. Termômetro de Oportunidades*\n"
            "• *O que mudou:* O bot analisa o histórico de preços e classifica as melhores ofertas.\n"
            "• *Como usar:* Suas notificações agora têm selos exclusivos:\n"
            "  🔥 `SUPER PROMOÇÃO`: Mais de 30% abaixo do preço normal!\n"
            "  🟢 `PREÇO EXCELENTE`: 15% a 30% abaixo da média.\n"
            "  🟡 `NA META`: Dentro do seu orçamento.\n\n"
            "⚡ *4. Filtro de Voos Diretos*\n"
            "• *O que mudou:* Agora você pode descartar voos com escalas.\n"
            "• *Como usar:* No assistente `/novo`, selecione a opção de voos diretos, ou diga para a IA: _\"Quero apenas voos diretos para o Rio\"_.\n\n"
            "👆 *5. Ações Rápidas em 1 Clique*\n"
            "• *O que mudou:* Cards interativos com botões inline.\n"
            "• *Como usar:* Envie `/listar` para ver seus alertas com botões `[🔄 Checar Agora]`, `[🗑️ Excluir]` e link direto no Google Flights.\n\n"
            "💬 *Dúvidas?* Digite `/ajuda` a qualquer momento para ver o guia completo."
        )

    @staticmethod
    async def enviar_broadcast(
        bot: Bot,
        destinatarios: List[Usuario],
        mensagem: str
    ) -> Dict[str, int]:
        total = len(destinatarios)
        sucessos = 0
        falhas = 0

        logging.info(f"Iniciando broadcast para {total} usuários autorizados...")

        for usuario in destinatarios:
            try:
                try:
                    await bot.send_message(
                        chat_id=usuario.user_id,
                        text=mensagem,
                        parse_mode="Markdown"
                    )
                except TelegramError as te:
                    logging.warning(f"Erro ao enviar Markdown para {usuario.user_id}: {te}. Tentando texto puro...")
                    await bot.send_message(
                        chat_id=usuario.user_id,
                        text=mensagem
                    )
                sucessos += 1
            except Exception as e:
                logging.error(f"Falha ao enviar broadcast para usuário {usuario.user_id} ({usuario.nome}): {e}")
                falhas += 1

            # Pausa de 50ms entre envios para respeitar o rate limit do Telegram
            await asyncio.sleep(0.05)

        logging.info(f"Broadcast finalizado. Sucessos: {sucessos}, Falhas: {falhas}")
        return {
            "total": total,
            "sucessos": sucessos,
            "falhas": falhas
        }
