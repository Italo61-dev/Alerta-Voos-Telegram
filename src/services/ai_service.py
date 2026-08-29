import json
import logging
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

class DadosAlertaIA(BaseModel):
    intencao: str = Field(
        description="criar_alerta se o usuário quer monitorar, criar alerta ou buscar passagem; duvida_viagem se for pergunta sobre turismo/épocas; outro se for conversa aleatória"
    )
    origem: Optional[str] = Field(default=None, description="Cidade ou aeroporto de origem informado")
    destino: Optional[str] = Field(default=None, description="Cidade ou aeroporto de destino informado")
    data_ida: Optional[str] = Field(default=None, description="Data de ida no formato AAAA-MM-DD")
    data_volta: Optional[str] = Field(default=None, description="Data de volta no formato AAAA-MM-DD, se informada")
    teto: Optional[float] = Field(default=None, description="Valor máximo ou teto em Reais (BRL) que o usuário quer pagar")
    resposta_direta: Optional[str] = Field(
        default=None, 
        description="Se for duvida_viagem ou faltar algum dado para criar o alerta, uma mensagem amigável e concisa em português para o usuário."
    )

class AIService:
    def __init__(self, api_key: Optional[str], model: str = "gemini-3.6-flash"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else None

    def disponivel(self) -> bool:
        return bool(self.client and self.api_key)

    def processar_mensagem(self, texto: str, hoje_iso: Optional[str] = None) -> Optional[DadosAlertaIA]:
        if not self.disponivel():
            logging.warning("AIService chamado mas chave GEMINI_API_KEY não está configurada.")
            return None

        hoje = hoje_iso or date.today().isoformat()
        prompt = (
            f"Você é o assistente inteligente de viagens de um bot de passagens aéreas no Telegram.\n"
            f"A data de hoje é {hoje}.\n\n"
            f"Mensagem do usuário: \"{texto}\"\n\n"
            "Instruções:\n"
            "1. Identifique se o usuário quer cadastrar ou buscar um alerta de voo ('criar_alerta') ou tirando dúvida ('duvida_viagem').\n"
            "2. Se for criar_alerta, extraia: origem, destino, data_ida (AAAA-MM-DD), data_volta (AAAA-MM-DD se houver) e teto em R$.\n"
            "3. Resolva termos relativos com base na data de hoje (ex: 'feriado de 15 de novembro', 'mês que vem', 'próxima sexta').\n"
            "4. Se o usuário esquecer algum dado crucial (ex: não informou o preço teto ou a data), preencha resposta_direta perguntando educadamente o que falta.\n"
            "5. Se for duvida_viagem, forneça uma dica útil e concisa de viagem em resposta_direta."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DadosAlertaIA,
                    temperature=0.2,
                ),
            )
            if response.text:
                dados = DadosAlertaIA.model_validate_json(response.text)
                return dados
        except APIError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logging.warning(f"Limite da API Gemini atingido (429): {e}")
                return DadosAlertaIA(
                    intencao="rate_limit",
                    resposta_direta=(
                        "⏳ *Limite temporário de IA atingido!*\n\n"
                        "A cota gratuita de inteligência artificial atingiu o limite de requisições por minuto.\n"
                        "Ela volta a funcionar em instantes. Enquanto isso, você pode usar os comandos normais:\n"
                        "✨ `/novo` - Assistente passo a passo\n"
                        "⚡ `/alerta` - Comando direto"
                    )
                )
            logging.error(f"Erro na API do Gemini: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado no AIService: {e}")

        return None
