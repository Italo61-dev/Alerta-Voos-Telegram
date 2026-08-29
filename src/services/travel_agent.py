import logging
from typing import Optional, Tuple, List, Dict, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

from src.models.alerta import Alerta
from src.database.alerta_repository import AlertaRepository
from src.services.airport_service import AirportService
from src.services.flight_service import FlightService
from src.services.date_service import DateService

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
        model: str = "gemini-3.5-flash-lite"
    ):
        self.client = client
        self.user_id = user_id
        self.alerta_repo = alerta_repo
        self.model = model
        self.ultimo_alerta_id: Optional[int] = None
        self.ultimo_link_flights: Optional[str] = None
        self._iniciar_chat()

    def _iniciar_chat(self):
        hoje = DateService.hoje_brasilia().isoformat()

        def buscar_voos_tempo_real(origem: str, destino: str, data_ida: str, data_volta: str = None) -> dict:
            """Busca opções de voos em tempo real no Google Flights.
            Args:
                origem: Cidade ou aeroporto de partida (ex: São Paulo, GRU, Brasília, BSB).
                destino: Cidade ou aeroporto de chegada (ex: Natal, NAT, Miami, MIA, Salvador).
                data_ida: Data de ida no formato AAAA-MM-DD.
                data_volta: Data de volta no formato AAAA-MM-DD (opcional se for só ida).
            """
            origem_iata = AirportService.resolver(origem) or origem.upper()
            destino_iata = AirportService.resolver(destino) or destino.upper()
            data_ida_iso = DateService.parse_data(data_ida) or data_ida
            data_volta_iso = DateService.parse_data(data_volta) if data_volta else None

            voos = FlightService.buscar_voos(origem_iata, destino_iata, data_ida_iso, data_volta_iso)
            link = FlightService.gerar_link_google_flights(origem_iata, destino_iata, data_ida_iso, data_volta_iso)
            self.ultimo_link_flights = link

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
                "total_encontrados": len(voos),
                "melhores_ofertas": top_3,
                "link_google_flights": link
            }

        def cadastrar_alerta_preco(origem: str, destino: str, data_ida: str, teto: float, data_volta: str = None) -> dict:
            """Cadastra e salva um alerta de monitoramento no banco de dados para avisar o usuário quando o preço baixar até o teto.
            Args:
                origem: Cidade ou aeroporto de saída (ex: Brasília, São Paulo).
                destino: Cidade ou aeroporto de destino (ex: Natal, Miami).
                data_ida: Data de ida no formato AAAA-MM-DD.
                teto: Valor máximo em Reais (BRL) que o usuário quer pagar (preço teto).
                data_volta: Data de volta no formato AAAA-MM-DD (opcional).
            """
            origem_iata = AirportService.resolver(origem) or origem.upper()
            destino_iata = AirportService.resolver(destino) or destino.upper()
            data_ida_iso = DateService.parse_data(data_ida) or data_ida
            data_volta_iso = DateService.parse_data(data_volta) if data_volta else None

            novo_alerta = Alerta(
                id=None,
                chat_id=self.user_id,
                origem=origem_iata,
                destino=destino_iata,
                teto=float(teto),
                data_ida=data_ida_iso,
                data_volta=data_volta_iso
            )
            alerta_id = self.alerta_repo.salvar(novo_alerta)
            self.ultimo_alerta_id = alerta_id

            link = FlightService.gerar_link_google_flights(origem_iata, destino_iata, data_ida_iso, data_volta_iso)
            self.ultimo_link_flights = link

            return {
                "status": "sucesso",
                "alerta_id": alerta_id,
                "origem": origem_iata,
                "destino": destino_iata,
                "teto": float(teto),
                "data_ida": data_ida_iso,
                "data_volta": data_volta_iso,
                "mensagem": f"Alerta #{alerta_id} gravado no banco de dados com sucesso e ativo para monitoramento periódico!"
            }

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
            "6. Se o usuário disser 'ok', 'sim', 'confirmo', 'pode salvar', 'beleza', e você já tiver as informações necessárias da viagem, chame cadastrar_alerta_preco para gravar no banco!\n"
            "7. Se o usuário pedir para ver os alertas dele ou cancelar algum alerta, use listar_alertas_cadastrados ou desativar_alerta.\n"
            "8. Dê dicas úteis sobre o destino e turismo sempre que couber."
        )

        self.chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=instrucoes,
                tools=[buscar_voos_tempo_real, cadastrar_alerta_preco, listar_alertas_cadastrados, desativar_alerta],
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

        modelos = [self.model, "gemini-3.7-flash", "gemini-3.6-flash"]
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
                break
            except Exception as e:
                ultimo_erro = e
                logging.error(f"Erro inesperado no TravelAgent ({mod}): {e}")
                break

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
