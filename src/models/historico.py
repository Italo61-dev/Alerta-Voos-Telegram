from dataclasses import dataclass
from typing import Optional

@dataclass
class RegistroHistorico:
    id: Optional[int]
    alerta_id: Optional[int]
    origem: str
    destino: str
    data_ida: str
    data_volta: Optional[str]
    preco: float
    companhia: str
    escalas: int
    consultado_em: Optional[str] = None

@dataclass
class EstatisticasTrecho:
    origem: str
    destino: str
    total_registros: int
    menor_preco: Optional[float] = None
    maior_preco: Optional[float] = None
    preco_medio: Optional[float] = None
    ultimo_preco: Optional[float] = None
    companhia_mais_barata: Optional[str] = None
