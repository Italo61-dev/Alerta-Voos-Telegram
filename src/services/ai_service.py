import json
import logging
from datetime import date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

class DadosAlertaIA(BaseModel):
    intencao: str = Field(
        description="criar_alerta (se quer monitorar preço); pesquisar_voos (se quer cotar agora); confirmar (se disse ok, sim, pode salvar, confirma); duvida_viagem; cancelar; outro"
    )
    origem: Optional[str] = Field(default=None, description="Cidade ou aeroporto de saída")
    destino: Optional[str] = Field(default=None, description="Cidade ou aeroporto de destino")
    data_ida: Optional[str] = Field(default=None, description="Data de ida no formato AAAA-MM-DD")
    data_volta: Optional[str] = Field(default=None, description="Data de volta no formato AAAA-MM-DD, se informada")
    teto: Optional[float] = Field(default=None, description="Valor máximo ou teto em Reais (BRL), se informado")
    resposta_direta: Optional[str] = Field(
        default=None, 
        description="Mensagem direta e amigável ao usuário quando faltar dados ou para tirar dúvidas de viagem."
    )

class AIService:
    def __init__(self, api_key: Optional[str], model: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else None

    def disponivel(self) -> bool:
        return bool(self.client and self.api_key)

    def processar_mensagem(
        self,
        texto: str,
        hoje_iso: Optional[str] = None,
        memoria_anterior: Optional[Dict[str, Any]] = None
    ) -> Optional[DadosAlertaIA]:
        if not self.disponivel():
            logging.warning("AIService chamado mas chave GEMINI_API_KEY não está configurada.")
            return None

        hoje = hoje_iso or date.today().isoformat()
        memoria_str = json.dumps(memoria_anterior or {}, ensure_ascii=False)

        prompt = (
            f"Você é o assistente inteligente de viagens de um bot de passagens aéreas no Telegram.\n"
            f"A data de hoje é {hoje}.\n\n"
            f"DADOS JÁ COLETADOS DESTA CONVERSA ANTERIORMENTE:\n"
            f"{memoria_str}\n\n"
            f"Mensagem atual do usuário: \"{texto}\"\n\n"
            "INSTRUÇÕES CRÍTICAS:\n"
            "1. MANTENHA A MEMÓRIA DA CONVERSA! O usuário conversa em etapas. Se ele já informou 'Natal' anteriormente e agora disse 'Saindo de SP', o destino continua Natal e a origem passa a ser São Paulo.\n"
            "2. Atualize os dados com novas informações enviadas ou corrija se o usuário pedir para mudar.\n"
            "3. Se o usuário disser 'cancelar', 'esquece' ou 'recomeçar', retorne intencao='cancelar'.\n"
            "4. REGRA DE OURO PARA INTENÇÃO: Se o usuário informou um preço máximo / teto que quer pagar (ex: 'quero pagar até 900', 'por até 800 reais', 'teto de 1500'), a intenção É SEMPRE 'criar_alerta'! Ele quer que o bot crie o alerta para monitorar e avisá-lo quando encontrar voo igual ou menor que aquele valor.\n"
            "5. Só marque 'pesquisar_voos' se ele NÃO informou teto de preço e pediu explicitamente para apenas ver/listar voos agora (ex: 'me dê 3 opções', 'pesquise voos de X para Y', 'quais os voos').\n"
            "6. Se for dúvida sobre turismo ou épocas baratas, marque 'duvida_viagem'.\n"
            "7. Se ainda faltar informações essenciais para concluir a viagem (ex: falta data ou de onde vai sair), preencha 'resposta_direta' confirmando com simpatia o que já sabe e perguntando o que falta (ex: 'Legal, anotado! De Brasília para Natal. Para qual data e valor você gostaria da viagem?')."
        )

        modelos = [self.model, "gemini-3.7-flash", "gemini-3.6-flash"]
        for mod in modelos:
            try:
                response = self.client.models.generate_content(
                    model=mod,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DadosAlertaIA,
                        temperature=0.1,
                    ),
                )
                if response.text:
                    return DadosAlertaIA.model_validate_json(response.text)
            except APIError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logging.warning(f"Limite da API Gemini atingido (429): {e}")
                    return DadosAlertaIA(
                        intencao="rate_limit",
                        resposta_direta=(
                            "⏳ *Limite temporário de IA atingido!*\n\n"
                            "A cota gratuita de inteligência artificial atingiu o limite de requisições por minuto.\n"
                            "Ela volta a funcionar em instantes. Enquanto isso, use o assistente `/novo`!"
                        )
                    )
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    logging.warning(f"Modelo {mod} retornou 503. Tentando fallback...")
                    continue
                logging.error(f"Erro na API do Gemini ({mod}): {e}")
                break
            except Exception as e:
                logging.error(f"Erro inesperado no AIService ({mod}): {e}")
                break

        return None

    def processar_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        hoje_iso: Optional[str] = None,
        memoria_anterior: Optional[Dict[str, Any]] = None
    ) -> Optional[DadosAlertaIA]:
        if not self.disponivel():
            logging.warning("AIService chamado mas chave GEMINI_API_KEY não está configurada.")
            return None

        hoje = hoje_iso or date.today().isoformat()
        memoria_str = json.dumps(memoria_anterior or {}, ensure_ascii=False)

        prompt = (
            f"Você é o assistente inteligente de viagens de um bot de passagens aéreas no Telegram.\n"
            f"A data de hoje é {hoje}.\n"
            f"DADOS JÁ COLETADOS DESTA CONVERSA:\n{memoria_str}\n\n"
            "O usuário enviou um áudio em anexo.\n"
            "1. Ouça com atenção e mantenha os dados da memória anterior somando com o que for dito no áudio.\n"
            "2. Se o usuário informou um preço máximo/teto que aceita pagar, a intenção É SEMPRE 'criar_alerta'! Se pediu apenas para ver/listar opções agora sem meta de preço, marque 'pesquisar_voos'.\n"
            "3. Se faltar dados para fechar o voo, pergunte com simpatia em 'resposta_direta'."
        )

        modelos = [self.model, "gemini-3.7-flash", "gemini-3.6-flash"]
        for mod in modelos:
            try:
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                response = self.client.models.generate_content(
                    model=mod,
                    contents=[audio_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DadosAlertaIA,
                        temperature=0.1,
                    ),
                )
                if response.text:
                    return DadosAlertaIA.model_validate_json(response.text)
            except APIError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logging.warning(f"Limite da API Gemini atingido (429) em áudio: {e}")
                    return DadosAlertaIA(
                        intencao="rate_limit",
                        resposta_direta=(
                            "⏳ *Limite temporário de IA atingido!*\n\n"
                            "A cota gratuita de inteligência artificial atingiu o limite de requisições por minuto.\n"
                            "Ela volta a funcionar em instantes. Enquanto isso, use o assistente `/novo`!"
                        )
                    )
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    continue
                logging.error(f"Erro na API do Gemini em áudio ({mod}): {e}")
                break
            except Exception as e:
                logging.error(f"Erro inesperado no AIService em áudio ({mod}): {e}")
                break

        return None
