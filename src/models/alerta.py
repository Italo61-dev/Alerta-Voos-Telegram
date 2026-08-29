from dataclasses import dataclass
from typing import Optional

@dataclass
class Alerta:
    id: Optional[int]
    chat_id: int
    origem: str
    destino: str
    teto: float
    data_ida: str
    data_volta: Optional[str] = None
    ultimo_preco: Optional[float] = None
    apenas_direto: bool = False
    ativo: bool = True
    criado_em: Optional[str] = None

    @property
    def is_ida_e_volta(self) -> bool:
        return bool(self.data_volta)
