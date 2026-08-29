import logging
from typing import Optional, Tuple, List, Dict, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

from src.models.alerta import Alerta
from src.database.alerta_repository import AlertaRepository
from src.database.historico_repository import HistoricoRepository
from src.services.airport_service import AirportService
from src.services.flight_service import FlightService
from src.services.date_service import DateService
from src.services.opportunity_service import OpportunityService

class TravelAgent:
    """
    Agente Conversacional Autônomo para o Telegram usando Function Calling nativo do Google Gemini.
    Mantém histórico de conversa real e executa ferramentas no Google Flights e no banco de dados.
    """
    def __init__(
        self,
        client: genai.Client,
        user_id: int,
        alerta_repo: AlertaRepository,
        historico_repo: Optional[HistoricoRepository] = None,
        model: str = "gemini-flash-lite-latest",
        max_alertas: int = 10,
        admin_id: Optional[int] = None
    ):
        self.client = client
        self.user_id = user_id
        self.alerta_repo = alerta_repo
        self.historico_repo = historico_repo
        self.model = model
        self.max_alertas = max_alertas
        self.admin_id = admin_id
        self.ultimo_alerta_id: Optional[int] = None
        self.ultimo_link_flights: Optional[str] = None
        self._iniciar_chat()

    def _iniciar_chat(self):
        hoje = DateService.hoje_brasilia().isoformat()

        def buscar_voos_tempo_real(
            origem: str,
            destino: str,
            data_ida: str,
            data_volta: str = None,
            apenas_direto: bool = False
        ) -> dict:
            """Busca opções de voos em tempo real no Google Flights.
            Args:
                origem: Cidade ou aeroporto de partida (ex: São Paulo, GRU, Brasília, BSB).
                destino: Cidade ou aeroporto de chegada (ex: Natal, NAT, Miami, MIA, Salvador).
                data_ida: Data de ida no formato AAAA-MM-DD.
                data_volta: Data de volta no formato AAAA-MM-DD (opcional se for só ida).
                apenas_direto: Defina como True se o usuário quer apenas voos diretos (sem escalas ou conexões).
            """
            origem_iata = AirportService.resolver(origem) or origem.upper()
            destino_iata = AirportService.resolver(destino) or destino.upper()
            data_ida_iso = DateService.parse_data(data_ida) or data_ida
            data_volta_iso = DateService.parse_data(data_volta) if data_volta else None

            voos = FlightService.buscar_voos(
                origem_iata,
                destino_iata,
                data_ida_iso,
                data_volta_iso,
                apenas_direto=apenas_direto
            )
            link = FlightService.gerar_link_google_flights(
                origem_iata,
                destino_iata,
                data_ida_iso,
                data_volta_iso,
                apenas_direto=apenas_direto
            )
            self.ultimo_link_flights = link

            # Registra a menor cotação encontrada no histórico do banco
            if voos and self.historico_repo:
                self.historico_repo.registrar(
                    origem=origem_iata,
                    destino=destino_iata,
                    data_ida=data_ida_iso,
                    preco=voos[0].preco,
                    companhia=voos[0].companhia,
                    escalas=voos[0].escalas,
                    data_volta=data_volta_iso
                )

            top_3 = [
                {
                    "preco_reais": v.preco,
                    "companhia": v.companhia,
                    "tipo": "Voo direto" if v.escalas == 0 else f"{v.escalas} conexão(ões)"
                }
                for v in voos[:3]
            ]
            return {
                "origem": origem_iata,
                "destino": destino_iata,
                "data_ida": data_ida_iso,
                "data_volta": data_volta_iso,
                "apenas_direto": apenas_direto,
                "total_encontrados": len(voos),
                "melhores_ofertas": top_3,
                "link_google_flights": link
            }

        def cadastrar_alerta_preco(
            origem: str,
            destino: str,
            data_ida: str,
            teto: float,
            data_volta: str = None,
            apenas_direto: bool = False
        ) -> dict:
            """Cadastra e salva um alerta de monitoramento no banco de dados para avisar o usuário quando o preço baixar até o teto.
            Args:
                origem: Cidade ou aeroporto de saída (ex: Brasília, São Paulo).
                destino: Cidade ou aeroporto de destino (ex: Natal, Miami).
                data_ida: Data de ida no formato AAAA-MM-DD.
                teto: Valor máximo em Reais (BRL) que o usuário quer pagar (preço teto).
                data_volta: Data de volta no formato AAAA-MM-DD (opcional).
                apenas_direto: Defina como True se o usuário especificou que quer somente voos diretos (sem escalas).
            """
            origem_iata = AirportService.resolver(origem) or origem.upper()
            destino_iata = AirportService.resolver(destino) or destino.upper()
            data_ida_iso = DateService.parse_data(data_ida) or data_ida
            data_volta_iso = DateService.parse_data(data_volta) if data_volta else None

            if self.admin_id is None or self.user_id != self.admin_id:
                total_ativos = self.alerta_repo.contar_ativos_por_usuario(self.user_id)
                if total_ativos >= self.max_alertas:
                    return {
                        "status": "limite_atingido",
                        "mensagem": (
                            f"O usuário já possui {total_ativos} alertas ativos, que é o limite máximo permitido ({self.max_alertas}). "
                            "Explique educadamente que ele atingiu o limite de alertas simultâneos e oriente-o a usar o comando /listar "
                            "para excluir alertas antigos antes de criar um novo."
                        )
                    }

            novo_alerta = Alerta(
                id=None,
                chat_id=self.user_id,
                origem=origem_iata,
                destino=destino_iata,
                teto=float(teto),
                data_ida=data_ida_iso,
                data_volta=data_volta_iso,
                apenas_direto=bool(apenas_direto)
            )
            alerta_id = self.alerta_repo.salvar(novo_alerta)
            self.ultimo_alerta_id = alerta_id

            link = FlightService.gerar_link_google_flights(
                origem_iata,
                destino_iata,
                data_ida_iso,
                data_volta_iso,
                apenas_direto=apenas_direto
            )
            self.ultimo_link_flights = link

            return {
                "status": "sucesso",
                "alerta_id": alerta_id,
                "origem": origem_iata,
                "destino": destino_iata,
                "teto": float(teto),
                "data_ida": data_ida_iso,
                "data_volta": data_volta_iso,
                "apenas_direto": apenas_direto,
                "mensagem": f"Alerta #{alerta_id} gravado no banco de dados com sucesso e ativo para monitoramento periódico!"
            }

        def consultar_historico_precos(origem: str, destino: str, data_ida: str = None, preco_atual: float = None) -> dict:
            """Consulta estatísticas históricas de preço registradas no banco para o trecho (menor preço já visto, média de mercado e termômetro de oportunidade).
            Args:
                origem: Cidade ou aeroporto de saída (ex: Brasília, BSB, São Paulo, GRU).
                destino: Cidade ou aeroporto de chegada (ex: Natal, NAT, Miami, MIA).
                data_ida: Data de ida no formato AAAA-MM-DD (opcional).
                preco_atual: Preço atual em Reais para avaliar no termômetro de oportunidade (opcional).
            """
            if not self.historico_repo:
                return {"status": "indisponivel", "mensagem": "Histórico não disponível no momento."}

            origem_iata = AirportService.resolver(origem) or origem.upper()
            destino_iata = AirportService.resolver(destino) or destino.upper()
            data_ida_iso = DateService.parse_data(data_ida) if data_ida else None

            stats = self.historico_repo.obter_estatisticas(origem_iata, destino_iata, data_ida_iso)
            if stats.total_registros == 0:
                return {
                    "trecho": f"{origem_iata} -> {destino_iata}",
                    "mensagem": "Ainda não acumulamos histórico de cotações suficiente para este trecho."
                }

            resultado = {
                "trecho": f"{origem_iata} -> {destino_iata}",
                "total_cotações_registradas": stats.total_registros,
                "menor_preco_historico": stats.menor_preco,
                "preco_medio": round(stats.preco_medio, 2) if stats.preco_medio else None,
                "maior_preco_historico": stats.maior_preco,
                "ultimo_preco_visto": stats.ultimo_preco,
                "companhia_mais_barata": stats.companhia_mais_barata
            }

            p_aval = preco_atual or stats.ultimo_preco
            if p_aval and stats.preco_medio:
                op = OpportunityService.classificar(p_aval, p_aval, stats.preco_medio)
                resultado["termometro_oportunidade"] = {
                    "classificacao": op.badge,
                    "descricao": op.descricao,
                    "desconto_percentual": f"{op.desconto_percentual:.1f}%"
                }

            return resultado

        def listar_alertas_cadastrados() -> dict:
            """Lista os alertas ativos que este usuário possui no banco de dados."""
            alertas = self.alerta_repo.listar_por_usuario(self.user_id)
            return {
                "alertas": [
                    {
                        "id": a.id,
                        "trecho": f"{a.origem} -> {a.destino}",
                        "teto_reais": a.teto,
                        "data_ida": a.data_ida,
                        "data_volta": a.data_volta,
                        "ultimo_preco": a.ultimo_preco
                    }
                    for a in alertas
                ]
            }

        def desativar_alerta(alerta_id: int) -> dict:
            """Desativa/exclui um alerta do usuário pelo ID."""
            sucesso = self.alerta_repo.desativar(alerta_id, self.user_id)
            return {
                "sucesso": sucesso,
                "mensagem": f"Alerta #{alerta_id} desativado com sucesso!" if sucesso else f"Alerta #{alerta_id} não encontrado."
            }

        instrucoes = (
            f"Você é a IA oficial de viagens e passagens aéreas no Telegram.\n"
            f"A data de hoje é {hoje}.\n\n"
            "DIRETRIZES DE ATUAÇÃO:\n"
            "1. Fale sempre em português brasileiro de forma acolhedora, animada, inteligente e prestativa.\n"
            "2. MANTENHA A MEMÓRIA DA CONVERSA! O usuário conversa em turnos naturais. Lembre-se do que ele já disse.\n"
            "3. Se o usuário falar um destino (ex: 'Quero ir para Natal'), pergunte com simpatia de onde ele vai sair, as datas e o orçamento teto.\n"
            "4. Se o usuário informar origem, destino, datas e um valor que aceita pagar (ex: 'quero pagar até 900 reais', 'teto de 1000'):\n"
            "   - Use cadastrar_alerta_preco para SALVAR IMEDIATAMENTE NO BANCO DE DADOS.\n"
            "   - Use buscar_voos_tempo_real para conferir como estão os preços agora e já dar essa informação de valor para o usuário.\n"
            "5. Se o usuário pedir apenas para ver opções de voos agora sem teto (ex: 'quais os voos de SP pra Salvador dia 15/11'), use buscar_voos_tempo_real e liste as melhores opções encontradas.\n"
            "6. Use o conceito do Termômetro de Oportunidade:\n"
            "   - 🔥 SUPER PROMOÇÃO (> 30% abaixo da média de mercado)\n"
            "   - 🟢 PREÇO EXCELENTE (15% a 30% abaixo da média de mercado)\n"
            "   - 🟡 NA META (dentro do orçamento do usuário)\n"
            "   Use consultar_historico_precos sempre que o usuário perguntar se um preço está barato ou se vale a pena comprar, e use as badges do termômetro para orientá-lo com entusiasmo!\n"
            "7. Se o usuário disser 'ok', 'sim', 'confirmo', 'pode salvar', 'beleza', e você já tiver as informações necessárias da viagem, chame cadastrar_alerta_preco para gravar no banco!\n"
            "8. Se o usuário pedir para ver os alertas dele ou cancelar algum alerta, use listar_alertas_cadastrados ou desativar_alerta.\n"
            "9. Dê dicas úteis sobre o destino e turismo sempre que couber."
        )

        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=instrucoes,
                tools=[
                    buscar_voos_tempo_real,
                    cadastrar_alerta_preco,
                    consultar_historico_precos,
                    listar_alertas_cadastrados,
                    desativar_alerta
                ],
                temperature=0.3
            )
        )

    def reiniciar(self):
        """Reinicia a sessão do chat para começar um novo atendimento do zero."""
        self._iniciar_chat()

    def enviar_mensagem(self, mensagem_ou_part) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Envia uma mensagem (texto ou audio Part) para o chat do agente.
        Retorna uma tupla: (texto_resposta, alerta_id_gerado, link_google_flights)
        """
        self.ultimo_alerta_id = None
        self.ultimo_link_flights = None

        modelos = [self.model]
        for m in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]:
            if m not in modelos:
                modelos.append(m)
        ultimo_erro = None

        for mod in modelos:
            try:
                if self.model != mod:
                    self.model = mod
                    self._iniciar_chat()
                resposta = self.chat.send_message(mensagem_ou_part)
                texto = resposta.text or "Entendido!"
                return texto, self.ultimo_alerta_id, self.ultimo_link_flights
            except APIError as e:
                ultimo_erro = e
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logging.warning(f"Limite temporário atingido no modelo {mod}: {e}")
                    continue
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    logging.warning(f"Modelo {mod} indisponível (503). Tentando próximo...")
                    continue
                logging.error(f"Erro na chamada do TravelAgent ({mod}): {e}")
                continue
            except Exception as e:
                ultimo_erro = e
                logging.warning(f"Exceção/Timeout no TravelAgent ({mod}): {e}. Tentando próximo modelo...")
                continue

        if ultimo_erro and ("429" in str(ultimo_erro) or "RESOURCE_EXHAUSTED" in str(ultimo_erro)):
            return (
                "⏳ *Limite temporário de IA atingido!*\n\n"
                "A cota gratuita de inteligência artificial atingiu o limite de requisições por minuto.\n"
                "Ela volta a funcionar em instantes. Enquanto isso, use o assistente `/novo`!",
                None,
                None
            )

        return (
            "Desculpe, tive uma instabilidade temporária ao consultar os voos. Poderia mandar sua mensagem novamente?",
            None,
            None
        )
