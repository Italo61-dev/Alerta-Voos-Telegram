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
- `/novo`: Assistente conversacional guiado passo a passo para criar alertas.
- `/novidades`: Guia com o que mudou no bot e exemplos de como usar cada função.
- `/alerta ORIGEM DESTINO TETO DATA_IDA [DATA_VOLTA]`: Criação rápida de alerta em linha.
- `/listar`: Exibe todos os seus alertas ativos com botões interativos de 1 clique.
- `/remover ID`: Desativa um alerta específico.
- `/testar`: Força checagem imediata dos seus alertas.
- *Mensagens de Texto e Áudio com IA:* Fale ou envie áudio naturalmente com o bot!

### Administrador:
- `/admin`: Central de comando interativa em botões (Estatísticas, Usuários, Transmissão e Checagem).
- `/stats`: Painel consolidado de métricas (usuários, alertas ativos, histórico de cotações e top rotas).
- `/usuarios`: Lista usuários registrados, status e ações.
- `/aprovar ID`: Aprova manualmente o acesso de um usuário.
- `/bloquear ID`: Bloqueia o acesso de um usuário.
- `/broadcast <msg>`: Transmite mensagem personalizada para todos os usuários autorizados.
- `/broadcast_novidades`: Dispara o resumo oficial de novidades e instruções para todos os usuários.

## ⚙️ Variáveis de Ambiente
- `TELEGRAM_TOKEN`: Token do bot gerado pelo @BotFather.
- `TURSO_DATABASE_URL`: URL do banco de dados Turso (ex: `libsql://...turso.io`).
- `TURSO_AUTH_TOKEN`: Token de autenticação do Turso.
- `ADMIN_ID`: ID numérico do Telegram do administrador (ex: `123456789`, obtido via @userinfobot).
