import logging
from typing import List, Optional
from urllib.parse import quote
from fast_flights import FlightQuery, create_query, get_flights
from src.models.voo import Voo

class FlightService:
    @staticmethod
    def buscar_voos(
        origem: str,
        destino: str,
        data_ida: str,
        data_volta: Optional[str] = None,
        apenas_direto: bool = False
    ) -> List[Voo]:
        try:
            if data_volta:
                flights = [
                    FlightQuery(date=data_ida, from_airport=origem, to_airport=destino),
                    FlightQuery(date=data_volta, from_airport=destino, to_airport=origem)
                ]
                trip_type = "round-trip"
            else:
                flights = [
                    FlightQuery(date=data_ida, from_airport=origem, to_airport=destino)
                ]
                trip_type = "one-way"

            resultados = None
            try:
                q = create_query(
                    flights=flights,
                    trip=trip_type,
                    currency="BRL",
                    language="pt-BR"
                )
                resultados = get_flights(q)
            except Exception as e_primary:
                # Fallback secundário para IPs internacionais de cloud (sem forçar pt-BR)
                try:
                    q_fallback = create_query(
                        flights=flights,
                        trip=trip_type,
                        currency="BRL"
                    )
                    resultados = get_flights(q_fallback)
                except Exception:
                    logging.warning(
                        f"Google Flights sem voos estruturados para {origem}->{destino} ({data_ida}): {e_primary}"
                    )
                    return []

            if not resultados:
                return []

            voos: List[Voo] = []
            for r in resultados:
                if hasattr(r, "price") and r.price is not None:
                    try:
                        p = float(r.price)
                        airlines = ", ".join(r.airlines) if hasattr(r, "airlines") and r.airlines else "Companhia Aérea"
                        stops = len(r.flights) - 1 if hasattr(r, "flights") and r.flights else 0
                        voos.append(Voo(preco=p, companhia=airlines, escalas=stops))
                    except (ValueError, TypeError):
                        continue

            if apenas_direto:
                voos = [v for v in voos if v.escalas == 0]

            voos.sort(key=lambda x: x.preco)
            return voos
        except Exception as e:
            logging.warning(f"Exceção ao processar busca {origem}->{destino} ({data_ida}): {e}")
            return []

    @staticmethod
    def gerar_link_google_flights(
        origem: str,
        destino: str,
        data_ida: str,
        data_volta: Optional[str] = None,
        apenas_direto: bool = False
    ) -> str:
        sufixo = " non-stop" if apenas_direto else ""
        if data_volta:
            termo = f"Flights to {destino} from {origem} on {data_ida} through {data_volta}{sufixo}"
        else:
            termo = f"Flights to {destino} from {origem} on {data_ida}{sufixo}"
        return f"https://www.google.com/travel/flights?q={quote(termo)}"
