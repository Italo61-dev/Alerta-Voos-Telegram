from enum import Enum
from typing import Optional
from dataclasses import dataclass

class NivelOportunidade(str, Enum):
    SUPER_PROMO = "SUPER_PROMO"  # > 30% abaixo da média histórica
    EXCELENTE   = "EXCELENTE"    # 15% a 30% abaixo da média histórica
    NA_META     = "NA_META"      # Preço atingiu ou ficou abaixo do teto
    REGULAR     = "REGULAR"      # Preço ainda acima do teto

@dataclass
class Oportunidade:
    nivel: NivelOportunidade
    badge: str
    titulo: str
    descricao: str
    desconto_percentual: float
    economia_reais: float

class OpportunityService:
    """
    Termômetro inteligente de oportunidade de preços para voos.
    Avalia descontos em relação à média histórica do trecho e teto do usuário.
    """

    @staticmethod
    def classificar(
        preco_atual: float,
        teto_usuario: float,
        preco_medio_historico: Optional[float] = None
    ) -> Oportunidade:
        # Se temos histórico com média válida
        if preco_medio_historico and preco_medio_historico > 0:
            economia = preco_medio_historico - preco_atual
            if economia > 0:
                desconto_pct = (economia / preco_medio_historico) * 100.0

                if desconto_pct >= 30.0:
                    return Oportunidade(
                        nivel=NivelOportunidade.SUPER_PROMO,
                        badge="🔥 SUPER PROMOÇÃO",
                        titulo="🔥 *SUPER PROMOÇÃO IMPERDÍVEL!*",
                        descricao=f"{desconto_pct:.0f}% abaixo da média de mercado (Economia de R$ {economia:.2f})",
                        desconto_percentual=desconto_pct,
                        economia_reais=economia
                    )
                elif desconto_pct >= 15.0:
                    return Oportunidade(
                        nivel=NivelOportunidade.EXCELENTE,
                        badge="🟢 PREÇO EXCELENTE",
                        titulo="🟢 *PREÇO EXCELENTE ENCONTRADO!*",
                        descricao=f"{desconto_pct:.0f}% abaixo da média de mercado (Economia de R$ {economia:.2f})",
                        desconto_percentual=desconto_pct,
                        economia_reais=economia
                    )

        # Se atingiu o teto estipulado pelo usuário
        if preco_atual <= teto_usuario:
            desconto_teto = ((teto_usuario - preco_atual) / teto_usuario) * 100.0 if teto_usuario > 0 else 0.0
            economia_teto = max(0.0, teto_usuario - preco_atual)
            desc = f"R$ {economia_teto:.2f} abaixo do seu teto!" if economia_teto > 0 else "Exatamente no valor do seu teto!"

            return Oportunidade(
                nivel=NivelOportunidade.NA_META,
                badge="🟡 NA META",
                titulo="🟡 *META DE PREÇO ATINGIDA!*",
                descricao=desc,
                desconto_percentual=desconto_teto,
                economia_reais=economia_teto
            )

        # Preço acima do teto
        diferenca_acima = preco_atual - teto_usuario
        return Oportunidade(
            nivel=NivelOportunidade.REGULAR,
            badge="⏳ ACIMA DA META",
            titulo="⏳ *Ainda Acima da Meta*",
            descricao=f"R$ {diferenca_acima:.2f} acima do seu teto estipulado",
            desconto_percentual=0.0,
            economia_reais=0.0
        )

    @staticmethod
    def badge_resumida(
        preco_atual: float,
        teto_usuario: float,
        preco_medio_historico: Optional[float] = None
    ) -> str:
        op = OpportunityService.classificar(preco_atual, teto_usuario, preco_medio_historico)
        return op.badge
