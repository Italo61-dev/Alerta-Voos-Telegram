from dataclasses import dataclass
from typing import Optional

@dataclass
class Usuario:
    user_id: int
    nome: str
    username: str
    autorizado: bool
    criado_em: Optional[str] = None
