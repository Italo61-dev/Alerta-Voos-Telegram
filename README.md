# ✈️ Bot de Alerta de Passagens Baratas (Telegram + Google Flights)

Bot do Telegram em Python que monitora preços de voos diretamente pelo Google Flights e alerta automaticamente quando o preço bate a meta estipulada.

## 🚀 Funcionalidades
- **Google Flights:** Sem custos de API corporativa, preços em R$ (BRL).
- **Banco em Nuvem (Turso/SQLite):** Alertas persistem na nuvem mesmo com reinicializações do servidor.
- **Checagem em Background:** Loop agendado a cada 3 horas.
- **Link Direto:** Dispara mensagem com o link pronto para reserva.
- **Modo Privado com Admin:** Solicitações de novos usuários com botões interativos de aprovação no Telegram.

## 📋 Comandos do Telegram

### Usuários Comuns:
- `/start` ou `/ajuda`: Mensagem de boas-vindas e instruções.
- `/alerta BSB NAT 500 2026-10-15`: Cadastra alerta só de ida.
- `/alerta BSB NAT 900 2026-10-15 2026-10-25`: Cadastra alerta de ida e volta.
- `/listar`: Exibe todos os seus alertas ativos cadastrados.
- `/remover ID`: Desativa um alerta específico.
- `/testar`: Força checagem imediata dos seus alertas.

### Administrador:
- `/usuarios`: Lista usuários registrados, status e ações.
- `/aprovar ID`: Aprova manualmente o acesso de um usuário.
- `/bloquear ID`: Bloqueia o acesso de um usuário.

## ⚙️ Variáveis de Ambiente
- `TELEGRAM_TOKEN`: Token do bot gerado pelo @BotFather.
- `TURSO_DATABASE_URL`: URL do banco de dados Turso (ex: `libsql://...turso.io`).
- `TURSO_AUTH_TOKEN`: Token de autenticação do Turso.
- `ADMIN_ID`: ID numérico do Telegram do administrador (`5599506814`).
