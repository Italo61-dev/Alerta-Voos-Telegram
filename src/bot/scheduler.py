from typing import Optional
from telegram import Bot
from src.config import Config
from src.database.alerta_repository import AlertaRepository
from src.database.historico_repository import HistoricoRepository
from src.services.flight_service import FlightService
from src.services.notifier_service import NotifierService

class AlertScheduler:
    def __init__(
        self,
        bot: Bot,
        config: Config,
        alerta_repo: AlertaRepository,
        historico_repo: Optional[HistoricoRepository] = None
    ):
        self.bot = bot
        self.config = config
        self.alerta_repo = alerta_repo
        self.historico_repo = historico_repo

    async def verificar_alertas(self) -> int:
        alertas = self.alerta_repo.listar_alertas_ativos(self.config.admin_id)
        if not alertas:
            return 0

        logging.info(f"Executando verificação periódica de {len(alertas)} alerta(s)...")
        notificados = 0

        for alerta in alertas:
            voos = FlightService.buscar_voos(
                origem=alerta.origem,
                destino=alerta.destino,
                data_ida=alerta.data_ida,
                data_volta=alerta.data_volta
            )
            if not voos:
                continue

            melhor_voo = voos[0]
            preco_atual = melhor_voo.preco

            # 1. Registra no histórico de preços para inteligência de mercado
            if self.historico_repo:
                self.historico_repo.registrar(
                    origem=alerta.origem,
                    destino=alerta.destino,
                    data_ida=alerta.data_ida,
                    preco=preco_atual,
                    companhia=melhor_voo.companhia,
                    escalas=melhor_voo.escalas,
                    data_volta=alerta.data_volta,
                    alerta_id=alerta.id
                )

            # 2. Atualiza o último preço registrado no alerta
            if alerta.id is not None:
                self.alerta_repo.atualizar_ultimo_preco(alerta.id, preco_atual)

            if preco_atual <= alerta.teto:
                deve_notificar = (alerta.ultimo_preco is None) or (preco_atual < alerta.ultimo_preco)
                if deve_notificar:

                    link = FlightService.gerar_link_google_flights(
                        origem=alerta.origem,
                        destino=alerta.destino,
                        data_ida=alerta.data_ida,
                        data_volta=alerta.data_volta
                    )
                    stats = self.historico_repo.obter_estatisticas(alerta.origem, alerta.destino, alerta.data_ida) if self.historico_repo else None
                    mensagem = NotifierService.mensagem_oferta_encontrada(alerta, melhor_voo, link, stats)

                    try:
                        botoes = NotifierService.botoes_notificacao_oferta(alerta.id, link)
                        await self.bot.send_message(
                            chat_id=alerta.chat_id,
                            text=mensagem,
                            reply_markup=botoes,
                            parse_mode="Markdown"
                        )
                        logging.info(f"Notificação disparada com sucesso para alerta #{alerta.id} (R$ {preco_atual:.2f})")
                        notificados += 1
                    except Exception as e:
                        logging.error(f"Erro ao enviar notificação para chat_id {alerta.chat_id}: {e}")

            # Pequeno intervalo para não sobrecarregar as consultas
            await asyncio.sleep(1)

        return notificados

    async def loop_agendado(self):
        # Aguarda 15 segundos após inicialização do bot para a primeira checagem
        await asyncio.sleep(15)
        intervalo_segundos = max(1, self.config.check_interval_hours) * 3600

        while True:
            try:
                await self.verificar_alertas()
            except Exception as e:
                logging.error(f"Erro no ciclo do loop agendado: {e}")
            await asyncio.sleep(intervalo_segundos)
