import os
import sqlite3
import logging
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from fast_flights import FlightQuery, create_query, get_flights

# 1. Configurações e Carregamento do Token
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DB_PATH = BASE_DIR / "alertas.db"

def carregar_token():
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_TOKEN="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("TELEGRAM_TOKEN", "8786563067:AAEZ-FItE9b_1KBsjUbP3MUZuta80lh05uc")

TELEGRAM_TOKEN = carregar_token()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 2. Servidor HTTP para compatibilidade com Render Web Service (Free Tier)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("✈️ Bot de Alerta de Passagens Online e Monitorando!".encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Silencia logs de health check para nao poluir o terminal

def iniciar_servidor_http():
    porta = int(os.environ.get("PORT", 8080))
    try:
        servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
        logging.info(f"Servidor HTTP de Health Check ativo na porta {porta}")
        servidor.serve_forever()
    except Exception as e:
        logging.warning(f"Não foi possível iniciar servidor HTTP na porta {porta}: {e}")

threading.Thread(target=iniciar_servidor_http, daemon=True).start()

# 3. Inicialização do Banco SQLite
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            teto REAL NOT NULL,
            data_ida TEXT NOT NULL,
            data_volta TEXT,
            ultimo_preco REAL,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 4. Consulta ao Google Flights via fast-flights
def buscar_voos_google(origem: str, destino: str, data_ida: str, data_volta: str = None) -> list:
    try:
        if data_volta:
            flights = [
                FlightQuery(date=data_ida, from_airport=origem, to_airport=destino),
                FlightQuery(date=data_volta, from_airport=destino, to_airport=origem)
            ]
            trip_type = "round-trip"
        else:
            flights = [
                FlightQuery(date=data_ida, from_airport=origem, to_airport=destino)
            ]
            trip_type = "one-way"

        q = create_query(
            flights=flights,
            trip=trip_type,
            currency="BRL",
            language="pt-BR"
        )
        
        resultados = get_flights(q)
        voos = []
        for r in resultados:
            if hasattr(r, "price") and r.price is not None:
                try:
                    p = float(r.price)
                    airlines = ", ".join(r.airlines) if hasattr(r, "airlines") and r.airlines else "Companhia Aérea"
                    voos.append({
                        "preco": p,
                        "companhia": airlines,
                        "stops": len(r.flights) - 1 if hasattr(r, "flights") and r.flights else 0
                    })
                except (ValueError, TypeError):
                    continue
        
        voos.sort(key=lambda x: x["preco"])
        return voos
    except Exception as e:
        logging.error(f"Erro ao consultar Google Flights para {origem}->{destino}: {e}")
        return []

# 5. Handlers de Comandos do Telegram

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(msg, parse_mode="Markdown")

async def alerta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) < 4:
        await update.message.reply_text(
            "⚠️ *Parâmetros insuficientes!*\n\n"
            "Use o formato:\n"
            "`/alerta ORIGEM DESTINO VALOR_TETO AAAA-MM-DD [AAAA-MM-DD]`\n\n"
            "*Exemplo:* `/alerta BSB NAT 500 2026-10-15`",
            parse_mode="Markdown"
        )
        return

    origem = args[0].upper().strip()
    destino = args[1].upper().strip()
    
    try:
        teto = float(args[2].replace("R$", "").replace(",", ".").strip())
    except ValueError:
        await update.message.reply_text("❌ *Valor teto inválido!* Digite apenas o número (ex: `500` ou `450.50`).", parse_mode="Markdown")
        return

    data_ida = args[3].strip()
    data_volta = args[4].strip() if len(args) > 4 else None

    try:
        datetime.strptime(data_ida, "%Y-%m-%d")
        if data_volta:
            datetime.strptime(data_volta, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ *Formato de data inválido!* Use o formato `AAAA-MM-DD` (ex: `2026-10-15`).", parse_mode="Markdown")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alertas (chat_id, origem, destino, teto, data_ida, data_volta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, origem, destino, teto, data_ida, data_volta))
    alerta_id = cursor.lastrowid
    conn.commit()
    conn.close()

    resposta = (
        f"🎯 *Alerta #{alerta_id} cadastrado com sucesso!*\n\n"
        f"🛫 *Trecho:* `{origem}` ➔ `{destino}`\n"
        f"💰 *Preço Teto:* R$ {teto:.2f}\n"
        f"📅 *Data de Ida:* {data_ida}\n"
    )
    if data_volta:
        resposta += f"📅 *Data de Volta:* {data_volta}\n"
    resposta += (
        f"\n🔍 Já estou de olho! Quando o preço bater ou ficar abaixo de *R$ {teto:.2f}*, "
        f"você receberá uma notificação aqui com o link para comprar no Google Flights."
    )
    await update.message.reply_text(resposta, parse_mode="Markdown")

async def listar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, origem, destino, teto, data_ida, data_volta, ultimo_preco
        FROM alertas
        WHERE chat_id = ? AND ativo = 1
        ORDER BY id DESC
    """, (chat_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            "📭 Você não possui nenhum alerta ativo no momento.\n"
            "Cadastre um com: `/alerta BSB NAT 500 2026-10-15`",
            parse_mode="Markdown"
        )
        return

    msg = "📋 *Seus Alertas Ativos:*\n\n"
    for r in rows:
        aid, origem, destino, teto, ida, volta, ult = r
        tipo = f"Ida ({ida}) e Volta ({volta})" if volta else f"Somente Ida ({ida})"
        msg += f"🔹 *Alerta #{aid}:* `{origem}` ➔ `{destino}`\n"
        msg += f"   • *Teto:* R$ {teto:.2f}\n"
        msg += f"   • *Datas:* {tipo}\n"
        if ult:
            msg += f"   • *Último menor preço:* R$ {ult:.2f}\n"
        msg += f"   • _Para remover:_ `/remover {aid}`\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def remover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text("⚠️ Informe o ID do alerta. Exemplo: `/remover 1`", parse_mode="Markdown")
        return

    try:
        alerta_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID deve ser um número inteiro.", parse_mode="Markdown")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE alertas SET ativo = 0 WHERE id = ? AND chat_id = ?", (alerta_id, chat_id))
    afetados = cursor.rowcount
    conn.commit()
    conn.close()

    if afetados > 0:
        await update.message.reply_text(f"🗑️ *Alerta #{alerta_id} removido com sucesso!*", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❓ Alerta #{alerta_id} não encontrado ou já removido.", parse_mode="Markdown")

# 6. Rotina de Verificação
async def checar_alertas(bot):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_id, origem, destino, teto, data_ida, data_volta, ultimo_preco FROM alertas WHERE ativo = 1")
    alertas = cursor.fetchall()
    conn.close()

    if not alertas:
        return

    logging.info(f"Executando verificação de {len(alertas)} alerta(s)...")

    for al in alertas:
        aid, chat_id, origem, destino, teto, ida, volta, ult_preco = al
        
        voos = buscar_voos_google(origem, destino, ida, volta)
        if not voos:
            continue

        melhor_voo = voos[0]
        preco_atual = melhor_voo["preco"]

        if preco_atual <= teto:
            if ult_preco is None or preco_atual < ult_preco:
                c = sqlite3.connect(DB_PATH)
                c.execute("UPDATE alertas SET ultimo_preco = ? WHERE id = ?", (preco_atual, aid))
                c.commit()
                c.close()

                if volta:
                    link_gflights = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{ida}%20through%20{volta}"
                else:
                    link_gflights = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origem}%20on%20{ida}"

                msg_alerta = (
                    f"🚨 *PREÇO BAIXOU! META ATINGIDA!* 🚨\n\n"
                    f"✈️ *Alerta #{aid}:* `{origem}` ➔ `{destino}`\n"
                    f"💵 *Preço Encontrado:* *R$ {preco_atual:.2f}*\n"
                    f"🎯 *Seu Preço Teto:* R$ {teto:.2f}\n"
                    f"🏢 *Companhia:* {melhor_voo['companhia']}\n"
                    f"📅 *Data:* {ida}" + (f" até {volta}" if volta else "") + "\n\n"
                    f"🔗 [Clique aqui para abrir a oferta no Google Flights]({link_gflights})"
                )

                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=msg_alerta,
                        parse_mode="Markdown"
                    )
                    logging.info(f"Notificação enviada com sucesso para alerta #{aid}!")
                except Exception as ex:
                    logging.error(f"Erro ao enviar mensagem Telegram: {ex}")

async def testar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *Consultando o Google Flights agora...*", parse_mode="Markdown")
    await checar_alertas(context.bot)
    await update.message.reply_text("✔️ *Consulta finalizada!* Se algum voo bateu seu preço teto, a notificação já foi enviada acima.", parse_mode="Markdown")

# 7. Agendador Assíncrono Nativo
async def loop_agendado(app):
    await asyncio.sleep(15)  # Primeira checagem 15 segundos após ligar
    while True:
        try:
            await checar_alertas(app.bot)
        except Exception as e:
            logging.error(f"Erro no loop agendado: {e}")
        await asyncio.sleep(10800)  # Checa a cada 3 horas (10800 segundos)

async def post_init(application):
    asyncio.create_task(loop_agendado(application))

# 8. Inicialização Principal
def main():
    print("Iniciando Bot de Alerta de Passagens...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ajuda", start_command))
    app.add_handler(CommandHandler("alerta", alerta_command))
    app.add_handler(CommandHandler("listar", listar_command))
    app.add_handler(CommandHandler("remover", remover_command))
    app.add_handler(CommandHandler("testar", testar_command))

    print("🤖 Bot pronto e escutando mensagens no Telegram!")
    app.run_polling()

if __name__ == "__main__":
    main()
