import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

class _HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("✈️ Bot de Alerta de Passagens Online e Monitorando!".encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Silencia logs de health check para manter terminal limpo

class HealthCheckServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        try:
            self._server = HTTPServer(("0.0.0.0", self.port), _HealthCheckHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logging.info(f"Servidor HTTP de Health Check ativo na porta {self.port}")
        except Exception as e:
            logging.warning(f"Não foi possível iniciar servidor HTTP na porta {self.port}: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            logging.info("Servidor HTTP de Health Check encerrado.")
