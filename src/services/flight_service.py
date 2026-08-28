import logging
from typing import List, Optional
from urllib.parse import quote
from fast_flights import FlightQuery, create_query, get_flights
from src.models.voo import Voo

class FlightService:
    @staticmethod
    def buscar_voos(origem: str, destino: str, data_ida: str, data_volta: Optional[str] = None) -> List[Voo]:
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

            q = create_query(
                flights=flights,
                trip=trip_type,
                currency="BRL",
                language="pt-BR"
            )

            resultados = get_flights(q)
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

            voos.sort(key=lambda x: x.preco)
            return voos
        except Exception as e:
            logging.error(f"Erro ao buscar voos {origem}->{destino} ({data_ida}): {e}")
            return []

    @staticmethod
    def gerar_link_google_flights(origem: str, destino: str, data_ida: str, data_volta: Optional[str] = None) -> str:
        if data_volta:
            termo = f"Flights to {destino} from {origem} on {data_ida} through {data_volta}"
        else:
            termo = f"Flights to {destino} from {origem} on {data_ida}"
        return f"https://www.google.com/travel/flights?q={quote(termo)}"
