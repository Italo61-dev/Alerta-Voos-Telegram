from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.middlewares import requer_autorizacao
from src.models.alerta import Alerta
from src.services.notifier_service import NotifierService
from src.services.flight_service import FlightService
from src.services.airport_service import AirportService
from src.services.date_service import DateService
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
            "*Exemplos:*\n"
            "• `/alerta BSB NAT 500 2026-10-15`\n"
            "• `/alerta \"São Paulo\" Miami 2500 2026-11-10`\n"
            "• `/alerta GRU LIS 4200 2026-11-10 2026-11-20`",
            parse_mode="Markdown"
        )
        return

    # Procura o índice do valor teto (primeiro argumento numérico)
    teto_idx = None
    for i, a in enumerate(args):
        val_clean = a.replace("R$", "").replace(",", ".").strip()
        try:
            val = float(val_clean)
            if val > 0 and i >= 2 and i < len(args) - 1:
                teto_idx = i
                break
        except ValueError:
            continue

    if teto_idx is not None:
        origem_raw = " ".join(args[:1] if teto_idx == 2 else args[:teto_idx - 1])
        destino_raw = " ".join(args[1:teto_idx] if teto_idx == 2 else args[teto_idx - 1:teto_idx])
        teto_raw = args[teto_idx]
        datas = args[teto_idx + 1:]
        data_ida = datas[0].strip()
        data_volta = datas[1].strip() if len(datas) > 1 else None
    else:
        origem_raw = args[0]
        destino_raw = args[1]
        teto_raw = args[2]
        data_ida = args[3].strip()
        data_volta = args[4].strip() if len(args) > 4 else None

    # Resolução de Cidades e IATA
    origem = AirportService.resolver(origem_raw)
    if not origem:
        await update.message.reply_text(
            f"❌ Não reconheci a cidade/aeroporto de origem: `{origem_raw}`.\n\n"
            "Use uma sigla de 3 letras (ex: `GRU`, `BSB`, `MIA`) ou o nome da cidade (ex: `São Paulo`, `Rio`, `Orlando`).",
            parse_mode="Markdown"
        )
        return

    destino = AirportService.resolver(destino_raw)
    if not destino:
        await update.message.reply_text(
            f"❌ Não reconheci a cidade/aeroporto de destino: `{destino_raw}`.\n\n"
            "Use uma sigla de 3 letras (ex: `NAT`, `MIA`, `LIS`) ou o nome da cidade (ex: `Salvador`, `Paris`, `Miami`).",
            parse_mode="Markdown"
        )
        return

    try:
        teto = float(teto_raw.replace("R$", "").replace(",", ".").strip())
        if teto <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "❌ *Valor teto inválido!* Digite um número positivo (ex: `500` ou `450.50`).",
            parse_mode="Markdown"
        )
        return

    data_ida_iso = DateService.parse_data(data_ida)
    if not data_ida_iso:
        await update.message.reply_text(
            f"❌ *Data de ida inválida:* `{data_ida}`\n\n"
            "Use o formato do dia a dia (ex: `15/10/2026` ou `15/10`) ou `2026-10-15`.",
            parse_mode="Markdown"
        )
        return

    data_volta_iso = None
    if data_volta:
        data_volta_iso = DateService.parse_data(data_volta)
        if not data_volta_iso:
            await update.message.reply_text(
                f"❌ *Data de volta inválida:* `{data_volta}`\n\n"
                "Use o formato do dia a dia (ex: `25/10/2026` ou `25/10`) ou `2026-10-25`.",
                parse_mode="Markdown"
            )
            return

        dt_ida = datetime.strptime(data_ida_iso, "%Y-%m-%d").date()
        dt_volta = datetime.strptime(data_volta_iso, "%Y-%m-%d").date()
        if dt_volta < dt_ida:
            await update.message.reply_text(
                "❌ *A data de volta não pode ser anterior à data de ida!*",
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
        data_ida=data_ida_iso,
        data_volta=data_volta_iso
    )
    alerta_id = alerta_repo.salvar(novo_alerta)
    novo_alerta.id = alerta_id

    resposta = NotifierService.mensagem_alerta_cadastrado(alerta_id, novo_alerta)
    link = FlightService.gerar_link_google_flights(origem, destino, data_ida_iso, data_volta_iso)
    botoes = NotifierService.botoes_card_alerta(novo_alerta, link)

    await update.message.reply_text(resposta, reply_markup=botoes, parse_mode="Markdown")

@requer_autorizacao
async def listar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    alerta_repo = context.bot_data["alerta_repo"]
    alertas = alerta_repo.listar_por_usuario(chat_id)

    if not alertas:
        await update.message.reply_text(
            "📭 *Você não possui nenhum alerta ativo no momento.*\n\n"
            "Para cadastrar, use:\n"
            "`/alerta BSB NAT 500 2026-10-15`\n"
            "Ou com cidades:\n"
            "`/alerta São Paulo Miami 2500 2026-11-10`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"📋 *Seus Alertas Ativos ({len(alertas)}):*\n"
        f"_Use os botões em cada alerta para checar o preço agora ou excluir com 1 clique._",
        parse_mode="Markdown"
    )

    historico_repo = context.bot_data.get("historico_repo")
    for al in alertas:
        link = FlightService.gerar_link_google_flights(
            origem=al.origem,
            destino=al.destino,
            data_ida=al.data_ida,
            data_volta=al.data_volta
        )
        stats = historico_repo.obter_estatisticas(al.origem, al.destino, al.data_ida) if historico_repo else None
        texto = NotifierService.mensagem_card_alerta(al, stats)
        botoes = NotifierService.botoes_card_alerta(al, link)
        await update.message.reply_text(texto, reply_markup=botoes, parse_mode="Markdown")

@requer_autorizacao
async def remover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "⚠️ Informe o ID do alerta. Exemplo: `/remover 1`\n"
            "💡 _Dica: Você também pode usar o botão '🗑️ Excluir' direto no comando /listar!_",
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
        f"✔️ *Consulta finalizada!* {notificados} notificação(ões) de preço enviada(s).",
        parse_mode="Markdown"
    )
