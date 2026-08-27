# ✈️ Bot de Alerta de Passagens Baratas (Telegram + Google Flights)

Bot do Telegram em Python que monitora preços de voos diretamente pelo Google Flights e alerta automaticamente quando o preço bate a meta estipulada.

## 🚀 Funcionalidades
- **Google Flights:** Sem custos de API corporativa, preços em R$ (BRL).
- **Persistência SQLite:** Alertas continuam salvos mesmo se reiniciar.
- **Checagem em Background:** Loop agendado a cada 3 horas.
- **Link Direto:** Dispara mensagem com o link pronto para reserva.

## 📋 Comandos do Telegram
- `/start` ou `/ajuda`: Mensagem de boas-vindas e instruções.
- `/alerta BSB NAT 500 2026-10-15`: Cadastra alerta só de ida.
- `/alerta BSB NAT 900 2026-10-15 2026-10-25`: Cadastra alerta de ida e volta.
- `/listar`: Exibe todos os alertas ativos cadastrados.
- `/remover ID`: Desativa um alerta pelo número do ID.
- `/testar`: Força checagem imediata de todos os alertas ativos.

## ☁️ Deploy no Render.com (24/7 Gratuito)
1. Crie um repositório privado no GitHub e suba este projeto.
2. Acesse [render.com](https://render.com) e conecte com seu GitHub.
3. Clique em **New +** e escolha **Background Worker** (ou **Web Service**).
4. Selecione o repositório.
5. Configurações:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
6. Em **Environment Variables**, adicione:
   - `TELEGRAM_TOKEN`: `seu_token_aqui`
7. Clique em **Deploy**!
