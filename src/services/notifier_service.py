from typing import List
from src.models.alerta import Alerta
from src.models.voo import Voo
from src.models.usuario import Usuario

class NotifierService:
    @staticmethod
    def mensagem_boas_vindas(is_admin: bool = False) -> str:
        msg = (
            "✈️ *Bem-vindo ao Bot de Alerta de Passagens Baratas!*\n\n"
            "Eu monitoro o *Google Flights* periodicamente e te aviso no Telegram "
            "assim que encontrar um voo com preço igual ou menor que a sua meta.\n\n"
            "📌 *Como cadastrar um alerta:*\n"
            "• *Somente Ida:*\n"
            "`/alerta ORIGEM DESTINO TETO DATA_IDA`\n"
            "_Exemplo:_ `/alerta BSB NAT 500 2026-10-15`\n\n"
            "• *Ida e Volta:*\n"
            "`/alerta ORIGEM DESTINO TETO DATA_IDA DATA_VOLTA`\n"
            "_Exemplo:_ `/alerta BSB NAT 900 2026-10-15 2026-10-25`\n\n"
            "📋 *Outros Comandos:*\n"
            "`/listar` - Ver todos os seus alertas cadastrados\n"
            "`/remover ID` - Desativar um alerta específico\n"
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
        msg = (
            f"🎯 *Alerta #{alerta_id} cadastrado com sucesso!*\n\n"
            f"🛫 *Trecho:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"💰 *Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"📅 *Data de Ida:* {alerta.data_ida}\n"
        )
        if alerta.data_volta:
            msg += f"📅 *Data de Volta:* {alerta.data_volta}\n"
        msg += (
            f"\n🔍 Já estou monitorando! Quando o preço atingir ou ficar abaixo de *R$ {alerta.teto:.2f}*, "
            f"você receberá uma notificação aqui com o link para comprar no Google Flights."
        )
        return msg

    @staticmethod
    def mensagem_oferta_encontrada(alerta: Alerta, voo: Voo, link_compra: str) -> str:
        escala_str = "Voo direto" if voo.escalas == 0 else f"{voo.escalas} conexão(ões)"
        datas = f"{alerta.data_ida}" + (f" até {alerta.data_volta}" if alerta.data_volta else "")
        return (
            f"🚨 *PREÇO BAIXOU! META ATINGIDA!* 🚨\n\n"
            f"✈️ *Alerta #{alerta.id}:* `{alerta.origem}` ➔ `{alerta.destino}`\n"
            f"💵 *Preço Encontrado:* *R$ {voo.preco:.2f}*\n"
            f"🎯 *Seu Preço Teto:* R$ {alerta.teto:.2f}\n"
            f"🏢 *Companhia:* {voo.companhia} ({escala_str})\n"
            f"📅 *Data:* {datas}\n\n"
            f"🔗 [Clique aqui para abrir a oferta no Google Flights]({link_compra})"
        )

    @staticmethod
    def mensagem_lista_alertas(alertas: List[Alerta]) -> str:
        if not alertas:
            return (
                "📭 Você não possui nenhum alerta ativo no momento.\n"
                "Cadastre um com: `/alerta BSB NAT 500 2026-10-15`"
            )

        msg = "📋 *Seus Alertas Ativos:*\n\n"
        for al in alertas:
            tipo = f"Ida ({al.data_ida}) e Volta ({al.data_volta})" if al.data_volta else f"Somente Ida ({al.data_ida})"
            msg += f"🔹 *Alerta #{al.id}:* `{al.origem}` ➔ `{al.destino}`\n"
            msg += f"   • *Teto:* R$ {al.teto:.2f}\n"
            msg += f"   • *Datas:* {tipo}\n"
            if al.ultimo_preco:
                msg += f"   • *Último menor preço:* R$ {al.ultimo_preco:.2f}\n"
            msg += f"   • _Para remover:_ `/remover {al.id}`\n\n"
        return msg

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
