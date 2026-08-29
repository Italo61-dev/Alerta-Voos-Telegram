from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.alerta import Alerta
from src.models.voo import Voo
from src.models.usuario import Usuario
from src.services.airport_service import AirportService
from src.services.date_service import DateService

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
            "`/testar` - Fazer uma checagem imediata de todos os seus alertas agora\n"
            "`/ajuda` - Reexibir esta mensagem"
        )
        if is_admin:
            msg += (
                "\n\n👑 *Comandos de Administrador:*\n"
                "`/usuarios` - Ver usuários e solicitações\n"
                "`/aprovar ID` - Aprovar acesso manualmente\n"
                "`/bloquear ID` - Bloquear acesso de um usuário"
            )
        return msg

    @staticmethod
    def mensagem_alerta_cadastrado(alerta_id: int, alerta: Alerta) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)

        msg = (
            f"🎯 *Alerta #{alerta_id} cadastrado com sucesso!*\n\n"
            f"🛫 *Trecho:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💰 *Preço Teto:* R$ {alerta.teto:.2f}\n"
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
    def mensagem_card_alerta(alerta: Alerta) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)
        tipo = f"Ida ({ida_br}) e Volta ({volta_br})" if alerta.data_volta else f"Somente Ida ({ida_br})"

        msg = (
            f"✈️ *Alerta #{alerta.id}*\n"
            f"🛫 *Trecho:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💰 *Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"📅 *Datas:* {tipo}\n"
        )
        if alerta.ultimo_preco:
            msg += f"💵 *Último menor preço:* R$ {alerta.ultimo_preco:.2f}\n"
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
    def mensagem_oferta_encontrada(alerta: Alerta, voo: Voo, link_compra: str) -> str:
        nome_origem = AirportService.nome_formatado(alerta.origem)
        nome_destino = AirportService.nome_formatado(alerta.destino)
        escala_str = "Voo direto" if voo.escalas == 0 else f"{voo.escalas} conexão(ões)"
        ida_br = DateService.formatar_br(alerta.data_ida)
        volta_br = DateService.formatar_br(alerta.data_volta)
        datas = f"{ida_br}" + (f" até {volta_br}" if volta_br else "")

        return (
            f"🚨 *PREÇO BAIXOU! META ATINGIDA!* 🚨\n\n"
            f"✈️ *Alerta #{alerta.id}:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"📍 _{nome_origem} ➔ {nome_destino}_\n"
            f"💵 *Preço Encontrado:* *R$ {voo.preco:.2f}*\n"
            f"🎯 *Seu Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"🏢 *Companhia:* {voo.companhia} ({escala_str})\n"
            f"📅 *Data:* {datas}\n\n"
            f"🔗 [Clique aqui para abrir a oferta no Google Flights]({link_compra})"
        )

    @staticmethod
    def botoes_notificacao_oferta(alerta_id: int, link_compra: str) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🔗 Comprar no Google Flights", url=link_compra)],
            [InlineKeyboardButton("🗑️ Excluir Alerta (Já comprei)", callback_data=f"remover_{alerta_id}")]
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
