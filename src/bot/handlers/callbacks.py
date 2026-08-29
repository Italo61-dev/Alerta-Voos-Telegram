import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from src.services.airport_service import AirportService
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService
from src.services.date_service import DateService
from src.services.opportunity_service import OpportunityService

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
            data_volta=alerta.data_volta,
            apenas_direto=alerta.apenas_direto
        )

        link = FlightService.gerar_link_google_flights(
            origem=alerta.origem,
            destino=alerta.destino,
            data_ida=alerta.data_ida,
            data_volta=alerta.data_volta,
            apenas_direto=alerta.apenas_direto
        )

        agora = DateService.hora_formatada_br()

        historico_repo = context.bot_data.get("historico_repo")
        if voos:
            melhor_voo = voos[0]
            preco_atual = melhor_voo.preco
            if alerta.id is not None:
                alerta_repo.atualizar_ultimo_preco(alerta.id, preco_atual)
            alerta.ultimo_preco = preco_atual

            if historico_repo:
                historico_repo.registrar(
                    origem=alerta.origem,
                    destino=alerta.destino,
                    data_ida=alerta.data_ida,
                    preco=preco_atual,
                    companhia=melhor_voo.companhia,
                    escalas=melhor_voo.escalas,
                    data_volta=alerta.data_volta,
                    alerta_id=alerta.id
                )

            stats = historico_repo.obter_estatisticas(alerta.origem, alerta.destino, alerta.data_ida) if historico_repo else None
            op = OpportunityService.classificar(
                preco_atual=preco_atual,
                teto_usuario=alerta.teto,
                preco_medio_historico=stats.preco_medio if (stats and stats.total_registros > 1) else None
            )
            status_meta = f"🏷️ *Termômetro:* `{op.badge}`\n💡 _{op.descricao}_"
            texto_atualizado = (
                f"{NotifierService.mensagem_card_alerta(alerta, stats)}\n"
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

    # 5. Confirmação de Alerta via IA
    elif data == "ai_confirmar":
        await query.answer()
        dados = context.user_data.pop("pendente_alerta_ia", None)
        context.user_data.pop("memoria_viagem", None)
        if not dados:
            await query.edit_message_text("⚠️ Os dados deste alerta expiraram. Envie sua frase novamente!")
            return

        from src.models.alerta import Alerta
        novo_alerta = Alerta(
            id=None,
            chat_id=user_id,
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

    elif data == "ai_cancelar":
        await query.answer()
        context.user_data.pop("pendente_alerta_ia", None)
        context.user_data.pop("memoria_viagem", None)
        await query.edit_message_text("❌ Alerta cancelado.")

    # 6. Criar Alerta a partir de Pesquisa Instantânea
    elif data == "ai_criar_alerta_busca":
        await query.answer()
        dados = context.user_data.get("pendente_alerta_ia")
        if not dados:
            await query.answer("⚠️ Dados da pesquisa expiraram. Faça uma nova pesquisa!", show_alert=True)
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        nome_origem = AirportService.nome_formatado(dados["origem"])
        nome_destino = AirportService.nome_formatado(dados["destino"])
        ida_br = DateService.formatar_br(dados["data_ida"])
        volta_br = DateService.formatar_br(dados.get("data_volta"))
        datas = f"Ida ({ida_br}) e Volta ({volta_br})" if dados.get("data_volta") else f"Somente Ida ({ida_br})"

        resumo = (
            "🔔 *Ativar Monitoramento Contínuo:*\n\n"
            f"🛫 *Trecho:* {nome_origem} ➔ {nome_destino}\n"
            f"📅 *Datas:* {datas}\n"
            f"💰 *Preço Teto Alvo:* R$ {dados['teto']:.2f}\n\n"
            "Deseja que eu monitore e te avise quando encontrar ofertas desse trecho?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmar e Ativar", callback_data="ai_confirmar"),
                InlineKeyboardButton("❌ Cancelar", callback_data="ai_cancelar")
            ]
        ]
        await query.message.reply_text(resumo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # 7. Menu e Ações Administrativas (/admin)
    elif data == "admin_menu":
        await query.answer()
        if user_id != config.admin_id:
            await query.answer("⛔ Acesso restrito ao administrador.", show_alert=True)
            return
        texto = NotifierService.mensagem_menu_admin()
        botoes = NotifierService.botoes_menu_admin()
        await query.edit_message_text(texto, reply_markup=botoes, parse_mode="Markdown")

    elif data == "admin_stats":
        await query.answer("Atualizando métricas...")
        if user_id != config.admin_id:
            await query.answer("⛔ Acesso restrito ao administrador.", show_alert=True)
            return
        historico_repo = context.bot_data.get("historico_repo")
        metricas_usuarios = usuario_repo.obter_metricas()
        metricas_alertas = alerta_repo.obter_metricas()
        metricas_historico = historico_repo.obter_metricas() if historico_repo else {}

        texto = NotifierService.mensagem_painel_stats(
            metricas_usuarios=metricas_usuarios,
            metricas_alertas=metricas_alertas,
            metricas_historico=metricas_historico
        )
        botoes = NotifierService.botoes_painel_stats()
        await query.edit_message_text(texto, reply_markup=botoes, parse_mode="Markdown")

    elif data == "admin_usuarios":
        await query.answer()
        if user_id != config.admin_id:
            await query.answer("⛔ Acesso restrito ao administrador.", show_alert=True)
            return
        usuarios = usuario_repo.listar_todos()
        texto = NotifierService.mensagem_lista_usuarios(usuarios, config.admin_id)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Menu Admin", callback_data="admin_menu")]]
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_broadcast_novidades":
        await query.answer("Iniciando transmissão...")
        if user_id != config.admin_id:
            await query.answer("⛔ Acesso restrito ao administrador.", show_alert=True)
            return
        from src.services.broadcast_service import BroadcastService
        destinatarios = usuario_repo.listar_autorizados()
        if not destinatarios:
            await query.edit_message_text("⚠️ Nenhum usuário autorizado encontrado para envio.")
            return

        mensagem_novidades = BroadcastService.formatar_mensagem_novidades()
        resultado = await BroadcastService.enviar_broadcast(
            bot=context.bot,
            destinatarios=destinatarios,
            mensagem=mensagem_novidades
        )
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Menu Admin", callback_data="admin_menu")]]
        await query.edit_message_text(
            f"🚀 *Novidades Transmitidas com Sucesso!*\n\n"
            f"👥 *Total de destinatários:* {resultado['total']}\n"
            f"✅ *Enviados com sucesso:* {resultado['sucessos']}\n"
            f"❌ *Falhas na entrega:* {resultado['falhas']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "admin_testar":
        await query.answer("Iniciando checagem agora...")
        if user_id != config.admin_id:
            await query.answer("⛔ Acesso restrito ao administrador.", show_alert=True)
            return
        from src.bot.scheduler import AlertScheduler
        scheduler = AlertScheduler(context.bot, config, alerta_repo)
        notificados = await scheduler.verificar_alertas()
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Menu Admin", callback_data="admin_menu")]]
        await query.edit_message_text(
            f"✔️ *Checagem concluída com sucesso!*\n\n"
            f"🔔 Notificações de ofertas enviadas: *{notificados}*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# Alias para retrocompatibilidade
callback_aprovacao = callback_geral
