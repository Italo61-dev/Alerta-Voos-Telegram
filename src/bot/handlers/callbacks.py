import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService

async def callback_geral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user_id = update.effective_user.id
    config = context.bot_data["config"]
    usuario_repo = context.bot_data["usuario_repo"]
    alerta_repo = context.bot_data["alerta_repo"]

    # 1. Aprovação de Usuário (Admin)
    if data.startswith("aprovar_"):
        await query.answer()
        if user_id != config.admin_id:
            await query.edit_message_text("⛔ Ação permitida apenas para o administrador.")
            return

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

    # 2. Recusa de Usuário (Admin)
    elif data.startswith("recusar_"):
        await query.answer()
        if user_id != config.admin_id:
            await query.edit_message_text("⛔ Ação permitida apenas para o administrador.")
            return

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

    # 3. Excluir Alerta com 1 Clique
    elif data.startswith("remover_"):
        await query.answer()
        try:
            alerta_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return

        alerta = alerta_repo.obter_por_id(alerta_id)
        if not alerta:
            await query.edit_message_text("❓ Alerta não encontrado ou já removido.")
            return

        if alerta.chat_id != user_id and user_id != config.admin_id:
            await query.answer("⛔ Você não tem permissão para excluir este alerta.", show_alert=True)
            return

        alerta_repo.desativar(alerta_id, alerta.chat_id)
        await query.edit_message_text(
            f"🗑️ *Alerta #{alerta_id} removido com sucesso!*\n"
            f"🛫 Trecho: `{alerta.origem}` ➔ `{alerta.destino}`",
            parse_mode="Markdown"
        )

    # 4. Checar Preço Instantaneamente com 1 Clique
    elif data.startswith("checar_"):
        try:
            alerta_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return

        alerta = alerta_repo.obter_por_id(alerta_id)
        if not alerta:
            await query.answer("❓ Alerta não encontrado.", show_alert=True)
            return

        if alerta.chat_id != user_id and user_id != config.admin_id:
            await query.answer("⛔ Você não tem permissão para consultar este alerta.", show_alert=True)
            return

        # Toast notification imediata na tela do usuário
        await query.answer("🔍 Consultando o Google Flights agora...")

        voos = FlightService.buscar_voos(
            origem=alerta.origem,
            destino=alerta.destino,
            data_ida=alerta.data_ida,
            data_volta=alerta.data_volta
        )

        link = FlightService.gerar_link_google_flights(
            origem=alerta.origem,
            destino=alerta.destino,
            data_ida=alerta.data_ida,
            data_volta=alerta.data_volta
        )

        agora = datetime.now().strftime("%H:%M:%S")

        if voos:
            melhor_voo = voos[0]
            preco_atual = melhor_voo.preco
            if alerta.id is not None:
                alerta_repo.atualizar_ultimo_preco(alerta.id, preco_atual)
            alerta.ultimo_preco = preco_atual

            status_meta = "🎯 *Preço bateu a meta!*" if preco_atual <= alerta.teto else f"⏳ *Acima da meta* (Teto: R$ {alerta.teto:.2f})"
            texto_atualizado = (
                f"{NotifierService.mensagem_card_alerta(alerta)}\n"
                f"⚡ *Última checagem ({agora}):*\n"
                f"💵 *Menor Preço Agora:* *R$ {preco_atual:.2f}* ({melhor_voo.companhia})\n"
                f"{status_meta}"
            )
            botoes = NotifierService.botoes_card_alerta(alerta, link)
            try:
                await query.edit_message_text(texto_atualizado, reply_markup=botoes, parse_mode="Markdown")
            except Exception as e:
                logging.warning(f"Não foi possível editar mensagem do alerta #{alerta_id}: {e}")
        else:
            await query.answer("⚠️ Nenhum voo encontrado para este trecho no Google Flights.", show_alert=True)

# Alias para retrocompatibilidade
callback_aprovacao = callback_geral
