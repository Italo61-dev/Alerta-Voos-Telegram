import unicodedata
from typing import Optional, Dict, Tuple

def _normalizar(texto: str) -> str:
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

class AirportService:
    # Mapeamento IATA -> Nome Descritivo
    AEROPORTOS: Dict[str, str] = {
        # Brasil - Sudeste
        "GRU": "São Paulo - Guarulhos",
        "CGH": "São Paulo - Congonhas",
        "VCP": "Campinas - Viracopos",
        "GIG": "Rio de Janeiro - Galeão",
        "SDU": "Rio de Janeiro - Santos Dumont",
        "CNF": "Belo Horizonte - Confins",
        "VIX": "Vitória",
        "UDI": "Uberlândia",
        "SJP": "São José do Rio Preto",
        "RAO": "Ribeirão Preto",

        # Brasil - Sul
        "CWB": "Curitiba - Afonso Pena",
        "FLN": "Florianópolis - Hercílio Luz",
        "POA": "Porto Alegre - Salgado Filho",
        "NVT": "Navegantes",
        "IGU": "Foz do Iguaçu",
        "JOI": "Joinville",
        "LDB": "Londrina",
        "MGF": "Maringá",
        "XAP": "Chapecó",

        # Brasil - Centro-Oeste
        "BSB": "Brasília - Pres. Juscelino Kubitschek",
        "GYN": "Goiânia - Santa Genoveva",
        "CGB": "Cuiabá - Mal. Rondon",
        "CGR": "Campo Grande",

        # Brasil - Nordeste
        "SSA": "Salvador - Dep. Luís Eduardo Magalhães",
        "FOR": "Fortaleza - Pinto Martins",
        "REC": "Recife - Guararapes",
        "NAT": "Natal - Aluízio Alves",
        "MCZ": "Maceió - Zumbi dos Palmares",
        "JPA": "João Pessoa - Castro Pinto",
        "AJU": "Aracaju - Santa Maria",
        "SLZ": "São Luís - Mal. Cunha Machado",
        "THE": "Teresina - Sen. Petrônio Portella",
        "BPS": "Porto Seguro",
        "ILH": "Ilhéus",
        "JDO": "Juazeiro do Norte",

        # Brasil - Norte
        "MAO": "Manaus - Eduardo Gomes",
        "BEL": "Belém - Val-de-Cans",
        "PMW": "Palmas",
        "PVH": "Porto Velho",
        "RBR": "Rio Branco",
        "MCP": "Macapá",
        "BVB": "Boa Vista",

        # Internacional - América do Norte
        "MIA": "Miami (EUA)",
        "MCO": "Orlando (EUA)",
        "JFK": "Nova York - JFK (EUA)",
        "EWR": "Nova York - Newark (EUA)",
        "LAX": "Los Angeles (EUA)",
        "LAS": "Las Vegas (EUA)",
        "ORD": "Chicago (EUA)",
        "BOS": "Boston (EUA)",
        "SFO": "São Francisco (EUA)",
        "YYZ": "Toronto (Canadá)",

        # Internacional - Europa
        "LIS": "Lisboa (Portugal)",
        "OPO": "Porto (Portugal)",
        "MAD": "Madri (Espanha)",
        "BCN": "Barcelona (Espanha)",
        "CDG": "Paris - Charles de Gaulle (França)",
        "ORY": "Paris - Orly (França)",
        "LHR": "Londres - Heathrow (Reino Unido)",
        "LGW": "Londres - Gatwick (Reino Unido)",
        "FCO": "Roma - Fiumicino (Itália)",
        "MXP": "Milão - Malpensa (Itália)",
        "AMS": "Amsterdã (Holanda)",
        "FRA": "Frankfurt (Alemanha)",
        "BER": "Berlim (Alemanha)",
        "ZRH": "Zurique (Suíça)",

        # Internacional - América do Sul
        "EZE": "Buenos Aires - Ezeiza (Argentina)",
        "AEP": "Buenos Aires - Aeroparque (Argentina)",
        "BRC": "Bariloche (Argentina)",
        "SCL": "Santiago (Chile)",
        "MVD": "Montevidéu (Uruguai)",
        "PDP": "Punta del Este (Uruguai)",
        "LIM": "Lima (Peru)",
        "BOG": "Bogotá (Colômbia)",
        "MDE": "Medellín (Colômbia)",
        "UIO": "Quito (Equador)",

        # Internacional - Caribe e América Central
        "CUN": "Cancún (México)",
        "MEX": "Cidade do México (México)",
        "PUJ": "Punta Cana (Rep. Dominicana)",
        "PTY": "Cidade do Panamá (Panamá)",

        # Internacional - Oriente Médio e Ásia
        "DXB": "Dubai (Emirados Árabes)",
        "DOH": "Doha (Catar)",
        "NRT": "Tóquio - Narita (Japão)",
        "HND": "Tóquio - Haneda (Japão)",
    }

    # Sinônimos e Cidades -> IATA principal
    SINONIMOS: Dict[str, str] = {
        # SP
        "sao paulo": "GRU",
        "sp": "GRU",
        "sampa": "GRU",
        "guarulhos": "GRU",
        "congonhas": "CGH",
        "campinas": "VCP",
        "viracopos": "VCP",

        # RJ
        "rio de janeiro": "GIG",
        "rio": "GIG",
        "rj": "GIG",
        "galeao": "GIG",
        "santos dumont": "SDU",

        # DF
        "brasilia": "BSB",
        "df": "BSB",

        # MG
        "belo horizonte": "CNF",
        "bh": "CNF",
        "confins": "CNF",
        "uberlandia": "UDI",

        # RS / PR / SC
        "porto alegre": "POA",
        "poa": "POA",
        "curitiba": "CWB",
        "florianopolis": "FLN",
        "floripa": "FLN",
        "foz do iguacu": "IGU",
        "foz": "IGU",
        "navegantes": "NVT",
        "londrina": "LDB",
        "maringa": "MGF",
        "chapeco": "XAP",
        "joinville": "JOI",

        # Nordeste
        "salvador": "SSA",
        "ssa": "SSA",
        "fortaleza": "FOR",
        "recife": "REC",
        "natal": "NAT",
        "maceio": "MCZ",
        "joao pessoa": "JPA",
        "aracaju": "AJU",
        "porto seguro": "BPS",
        "ilheus": "ILH",
        "sao luis": "SLZ",
        "teresina": "THE",

        # Norte / CO
        "manaus": "MAO",
        "belem": "BEL",
        "goiania": "GYN",
        "cuiaba": "CGB",
        "campo grande": "CGR",
        "vitoria": "VIX",

        # Exterior
        "miami": "MIA",
        "orlando": "MCO",
        "nova york": "JFK",
        "new york": "JFK",
        "ny": "JFK",
        "nyc": "JFK",
        "los angeles": "LAX",
        "las vegas": "LAS",
        "boston": "BOS",
        "chicago": "ORD",
        "san francisco": "SFO",
        "sao francisco": "SFO",
        "toronto": "YYZ",

        "lisboa": "LIS",
        "lisbon": "LIS",
        "porto portugal": "OPO",
        "madri": "MAD",
        "madrid": "MAD",
        "barcelona": "BCN",
        "paris": "CDG",
        "londres": "LHR",
        "london": "LHR",
        "roma": "FCO",
        "rome": "FCO",
        "milao": "MXP",
        "milan": "MXP",
        "amsterda": "AMS",
        "amsterdam": "AMS",
        "frankfurt": "FRA",
        "berlim": "BER",
        "zurique": "ZRH",

        "buenos aires": "EZE",
        "bsas": "EZE",
        "bariloche": "BRC",
        "santiago": "SCL",
        "montevideu": "MVD",
        "montevideo": "MVD",
        "punta del este": "PDP",
        "lima": "LIM",
        "bogota": "BOG",
        "medellin": "MDE",
        "cancun": "CUN",
        "punta cana": "PUJ",
        "dubai": "DXB",
        "toquio": "NRT",
        "tokyo": "NRT",
    }

    @classmethod
    def resolver(cls, termo: str) -> Optional[str]:
        if not termo:
            return None

        termo_limpo = termo.strip().upper()
        norm = _normalizar(termo)

        # 1. Se estiver nos sinônimos e cidades mapeadas
        if norm in cls.SINONIMOS:
            return cls.SINONIMOS[norm]

        # 2. Se já for um IATA direto conhecido
        if termo_limpo in cls.AEROPORTOS:
            return termo_limpo

        # 3. Se for 3 letras alfabéticas (código IATA qualquer)
        if len(termo_limpo) == 3 and termo_limpo.isalpha():
            return termo_limpo

        # 4. Busca parcial no dicionário descritivo
        for iata, desc in cls.AEROPORTOS.items():
            if norm in _normalizar(desc):
                return iata

        return None

    @classmethod
    def nome_formatado(cls, iata: str) -> str:
        iata_upper = iata.strip().upper()
        desc = cls.AEROPORTOS.get(iata_upper)
        if desc:
            return f"{desc} ({iata_upper})"
        return iata_upper
