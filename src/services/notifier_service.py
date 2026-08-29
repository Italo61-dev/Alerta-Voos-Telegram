from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.alerta import Alerta
from src.models.voo import Voo
from src.models.usuario import Usuario
from src.models.historico import EstatisticasTrecho
from src.services.airport_service import AirportService
from src.services.date_service import DateService
from src.services.opportunity_service import OpportunityService

class NotifierService:
    @staticmethod
    def mensagem_boas_vindas(is_admin: bool = False) -> str:
        msg = (
            "✈️ *Bem-vindo ao Bot de Alerta de Passagens Baratas!*\n\n"
            "Eu monitoro o *Google Flights* periodicamente e te aviso no Telegram "
            "assim que encontrar um voo com preço igual ou menor que a sua meta.\n\n"
            "📌 *Como cadastrar um alerta:*\n"
            "💬 *Mensagem natural com IA:* Apenas fale comigo!\n"
            "_Exemplo:_ `Quero ir de SP pro Rio no feriado de 15 de novembro por até 450 reais`\n\n"
            "✨ `/novo` - *Assistente guiado passo a passo* com botões\n"
            "⚡ `/alerta ORIGEM DESTINO TETO DATA_IDA [DATA_VOLTA]` - Comando rápido em uma linha\n"
            "_Exemplo:_ `/alerta São Paulo Miami 2500 10/11/2026`\n\n"
            "💡 _Dica: Você também pode me fazer perguntas de viagem, dicas de turismo e épocas baratas!_\n\n"
            "📋 *Outros Comandos:*\n"
            "`/listar` - Ver seus alertas em cards interativos com botões\n"
            "`/novidades` - Ver o que há de novo no bot e como usar as novas funções\n"
            "`/testar` - Fazer uma checagem imediata de todos os seus alertas agora\n"
            "`/ajuda` - Reexibir esta mensagem"
        )
        if is_admin:
            msg += (
                "\n\n👑 *Comandos de Administrador:*\n"
                "`/admin` - Painel de controle central interativo\n"
                "`/stats` - Painel de estatísticas e métricas de uso\n"
                "`/usuarios` - Ver usuários e solicitações\n"
                "`/aprovar ID` - Aprovar acesso manualmente\n"
                "`/bloquear ID` - Bloquear acesso de um usuário\n"
                "`/broadcast <msg>` - Transmitir mensagem para todos os usuários\n"
                "`/broadcast_novidades` - Disparar comunicado de novidades para todos"
            )
        return msg

    @staticmethod
    def mensagem_alerta_cadastrado(alerta_id: int, alerta: Alerta) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)

        escala_info = "⚡ Somente voos diretos" if alerta.apenas_direto else "🔄 Voos diretos ou com conexão"

        msg = (
            f"🎯 *Alerta #{alerta_id} cadastrado com sucesso!*\n\n"
            f"🛫 *Trecho:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💰 *Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"✈️ *Filtro:* {escala_info}\n"
            f"📅 *Data de Ida:* {ida_br}\n"
        )
        if alerta.data_volta:
            msg += f"📅 *Data de Volta:* {volta_br}\n"
        msg += (
            f"\n🔍 Já estou monitorando! Quando o preço atingir ou ficar abaixo de *R$ {alerta.teto:.2f}*, "
            f"você receberá uma notificação aqui com link e botões de ação rápida."
        )
        return msg

    @staticmethod
    def mensagem_card_alerta(alerta: Alerta, stats: Optional[EstatisticasTrecho] = None) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)
        tipo = f"Ida ({ida_br}) e Volta ({volta_br})" if alerta.data_volta else f"Somente Ida ({ida_br})"
        escala_tag = " `[Apenas Direto]`" if alerta.apenas_direto else ""

        msg = (
            f"✈️ *Alerta #{alerta.id}*{escala_tag}\n"
            f"🛫 *Trecho:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💰 *Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"📅 *Datas:* {tipo}\n"
        )
        if alerta.ultimo_preco:
            badge = OpportunityService.badge_resumida(
                preco_atual=alerta.ultimo_preco,
                teto_usuario=alerta.teto,
                preco_medio_historico=stats.preco_medio if (stats and stats.total_registros > 1) else None
            )
            msg += f"💵 *Último menor preço:* R$ {alerta.ultimo_preco:.2f}  `[{badge}]`\n"

        if stats and stats.total_registros > 1 and stats.menor_preco:
            msg += (
                f"📈 *Histórico:* Menor já visto: R$ {stats.menor_preco:.2f} | "
                f"Média: R$ {stats.preco_medio:.2f}\n"
            )
        return msg

    @staticmethod
    def botoes_card_alerta(alerta: Alerta, link_compra: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🔗 Abrir no Google Flights", url=link_compra)],
            [
                InlineKeyboardButton("🔄 Checar Agora", callback_data=f"checar_{alerta.id}"),
                InlineKeyboardButton("🗑️ Excluir", callback_data=f"remover_{alerta.id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def mensagem_oferta_encontrada(
        alerta: Alerta,
        voo: Voo,
        link_compra: str,
        stats: Optional[EstatisticasTrecho] = None
    ) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        escala_str = "Voo direto" if voo.escalas == 0 else f"{voo.escalas} conexão(ões)"
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)
        datas = f"{ida_br}" + (f" até {volta_br}" if volta_br else "")

        # Classificação inteligente de oportunidade
        op = OpportunityService.classificar(
            preco_atual=voo.preco,
            teto_usuario=alerta.teto,
            preco_medio_historico=stats.preco_medio if (stats and stats.total_registros > 1) else None
        )

        msg = (
            f"{op.titulo}\n"
            f"🏷️ *Termômetro:* `{op.badge}`\n"
            f"💡 _{op.descricao}_\n\n"
            f"✈️ *Alerta #{alerta.id}:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💵 *Preço Encontrado:* *R$ {voo.preco:.2f}*\n"
            f"🎯 *Seu Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"🏢 *Companhia:* {voo.companhia} ({escala_str})\n"
            f"📅 *Data:* {datas}\n"
        )
        if stats and stats.total_registros > 1 and stats.menor_preco:
            msg += f"📈 *Histórico:* Menor já visto: R$ {stats.menor_preco:.2f} | Média: R$ {stats.preco_medio:.2f}\n"

        msg += f"\n🔗 [Clique aqui para abrir a oferta no Google Flights]({link_compra})"
        return msg

    @staticmethod
    def botoes_notificacao_oferta(alerta_id: int, link_compra: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🔗 Comprar no Google Flights", url=link_compra)],
            [InlineKeyboardButton("🗑️ Excluir Alerta (Já comprei)", callback_data=f"remover_{alerta_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def mensagem_resultado_busca(origem: str, destino: str, data_ida: str, data_volta: Optional[str], voos: List[Voo]) -> str:
        nome_origem = AirportService.nome_formatado(origem)
        nome_destino = AirportService.nome_formatado(destino)
        ida_br = DateService.formatar_br(data_ida)
        volta_br = DateService.formatar_br(data_volta)
        datas = f"Ida ({ida_br}) e Volta ({volta_br})" if data_volta else f"Somente Ida ({ida_br})"

        msg = (
            f"🔍 *Melhores Opções no Google Flights:*\n\n"
            f"🛫 *Trecho:* `{origem}` ➔ `{destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"📅 *Datas:* {datas}\n\n"
        )
        if not voos:
            msg += "⚠️ Nenhum voo com preço disponível encontrado para esta data no Google Flights no momento.\n"
            return msg

        qtd = min(len(voos), 3)
        msg += f"🏆 *Top {qtd} Menores Preços Encontrados:*\n\n"
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, v in enumerate(voos[:3]):
            emoji = emojis[i] if i < len(emojis) else "✈️"
            escala = "Voo direto" if v.escalas == 0 else f"{v.escalas} conexão(ões)"
            msg += f"{emoji} *R$ {v.preco:.2f}* — {v.companhia} ({escala})\n"

        return msg

    @staticmethod
    def botoes_resultado_busca(link_compra: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🔗 Ver Todos no Google Flights", url=link_compra)],
            [InlineKeyboardButton("🔔 Criar Alerta para este Trecho", callback_data="ai_criar_alerta_busca")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def mensagem_lista_usuarios(usuarios: List[Usuario], admin_id: int) -> str:
        if not usuarios:
            return "Nenhum usuário registrado."

        msg = "👥 *Painel de Usuários:*\n\n"
        for u in usuarios:
            status = "✅ Autorizado" if u.autorizado else "⏳ Pendente/Bloqueado"
            eh_admin = u.user_id == admin_id
            admin_tag = " 👑 *(Você)*" if eh_admin else ""
            uname = f"@{u.username}" if u.username else "sem username"
            msg += f"• *{u.nome}*{admin_tag} ({uname})\n  🆔 `{u.user_id}` | {status}\n"
            if not eh_admin:
                msg += f"  _Ações:_ `/aprovar {u.user_id}` | `/bloquear {u.user_id}`\n"
            msg += "\n"
        return msg

    @staticmethod
    def mensagem_painel_stats(
        metricas_usuarios: dict,
        metricas_alertas: dict,
        metricas_historico: dict
    ) -> str:
        msg = (
            "📊 *PAINEL DE ESTATÍSTICAS DO BOT* 👑\n\n"
            "👥 *Usuários Cadastrados:*\n"
            f"• Total Geral: *{metricas_usuarios.get('total', 0)}*\n"
            f"• Autorizados / Ativos: *{metricas_usuarios.get('autorizados', 0)}*\n"
            f"• Pendentes / Bloqueados: *{metricas_usuarios.get('pendentes', 0)}*\n\n"
            "✈️ *Monitoramento de Voos:*\n"
            f"• Alertas Ativos no Momento: *{metricas_alertas.get('ativos', 0)}*\n"
            f"• Total Histórico de Alertas: *{metricas_alertas.get('total_historico', 0)}*\n\n"
            "📈 *Histórico de Cotações (Google Flights):*\n"
            f"• Total de Cotações Registradas: *{metricas_historico.get('total_cotacoes', 0):,}*\n"
            f"• Trechos Únicos Cotados: *{metricas_historico.get('trechos_unicos', 0)}*\n"
        ).replace(",", ".")

        top_trechos = metricas_alertas.get("top_trechos", [])
        if top_trechos:
            msg += "\n🏆 *Top Trechos Mais Procurados:*\n"
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            for idx, item in enumerate(top_trechos):
                em = emojis[idx] if idx < len(emojis) else "✈️"
                orig = item["origem"]
                dest = item["destino"]
                qtd = item["quantidade"]
                msg += f"{em} `{orig}` ➔ `{dest}`: *{qtd}* alerta(s)\n"

        return msg

    @staticmethod
    def botoes_painel_stats() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("🔄 Atualizar Métricas", callback_data="admin_stats"),
                InlineKeyboardButton("🔙 Menu Admin", callback_data="admin_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def mensagem_menu_admin() -> str:
        return (
            "👑 *CENTRAL DE CONTROLE DO ADMINISTRADOR*\n\n"
            "Escolha uma ação rápida abaixo para gerenciar o bot sem misturar com suas conversas pessoais:"
        )

    @staticmethod
    def botoes_menu_admin() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("📊 Estatísticas (/stats)", callback_data="admin_stats"),
                InlineKeyboardButton("👥 Usuários (/usuarios)", callback_data="admin_usuarios")
            ],
            [
                InlineKeyboardButton("📢 Disparar Novidades", callback_data="admin_broadcast_novidades"),
                InlineKeyboardButton("⚡ Checar Voos Agora", callback_data="admin_testar")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
