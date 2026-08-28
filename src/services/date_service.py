from datetime import datetime, date
from typing import Optional

class DateService:
    @staticmethod
    def parse_data(texto: str) -> Optional[str]:
        """
        Converte datas informadas em múltiplos formatos humanos (brasileiro ou ISO)
        para o formato padrão do Google Flights/banco: 'AAAA-MM-DD'.
        
        Suporta:
        - DD/MM/AAAA (ex: 15/11/2026)
        - DD/MM/AA   (ex: 15/11/26)
        - DD/MM      (ex: 15/11 - calcula ano atual ou próximo se já passou)
        - DD-MM-AAAA (ex: 15-11-2026)
        - AAAA-MM-DD (ex: 2026-11-15 - formato ISO para desenvolvedores)
        """
        if not texto:
            return None

        texto = texto.strip()

        # 1. Verifica formato ISO YYYY-MM-DD
        if "-" in texto and len(texto.split("-")[0]) == 4:
            try:
                dt = datetime.strptime(texto, "%Y-%m-%d").date()
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None

        texto_limpo = texto.replace(".", "/").replace("-", "/")
        partes = texto_limpo.split("/")
        hoje = date.today()

        # 2. Formato DD/MM (dia e mês sem ano)
        if len(partes) == 2:
            try:
                dia, mes = int(partes[0]), int(partes[1])
                ano = hoje.year
                dt = date(ano, mes, dia)
                if dt < hoje:
                    ano += 1
                    dt = date(ano, mes, dia)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return None

        # 3. Formato DD/MM/AAAA ou DD/MM/AA
        if len(partes) == 3:
            p0, p1, p2 = partes[0], partes[1], partes[2]
            try:
                if len(p0) == 4:  # YYYY/MM/DD
                    dt = datetime.strptime(texto_limpo, "%Y/%m/%d").date()
                elif len(p2) == 2:  # DD/MM/YY
                    dt = datetime.strptime(texto_limpo, "%d/%m/%y").date()
                else:  # DD/MM/YYYY
                    dt = datetime.strptime(texto_limpo, "%d/%m/%Y").date()
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None

        return None

    @staticmethod
    def formatar_br(data_iso: Optional[str]) -> str:
        """
        Converte uma data ISO (AAAA-MM-DD) para exibição amigável brasileira (DD/MM/AAAA).
        """
        if not data_iso:
            return ""
        try:
            dt = datetime.strptime(data_iso.strip(), "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(data_iso)
