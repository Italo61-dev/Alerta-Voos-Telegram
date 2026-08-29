import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.config import Config
from src.database.connection import DatabaseManager
from src.database.schema import init_db
from src.database.usuario_repository import UsuarioRepository
from src.database.alerta_repository import AlertaRepository
from src.database.historico_repository import HistoricoRepository
from src.models.alerta import Alerta
from src.services.notifier_service import NotifierService
from src.bot.handlers.admin_handlers import stats_command, admin_command

class TestStats(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.config = Config(
            telegram_token="TEST_TOKEN",
            admin_id=1001,
            gemini_api_key="TEST_KEY",
            turso_database_url=None,
            turso_auth_token=None,
            check_interval_hours=1,
            port=8080,
            db_path=Path(self.temp_db.name)
        )
        self.db_manager = DatabaseManager(self.config)
        init_db(self.config)
        self.usuario_repo = UsuarioRepository(self.db_manager)
        self.alerta_repo = AlertaRepository(self.db_manager)
        self.historico_repo = HistoricoRepository(self.db_manager)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_metricas_usuarios(self):
        # Inicialmente admin_id já é inserido no init_db
        metricas = self.usuario_repo.obter_metricas()
        self.assertEqual(metricas["total"], 1)
        self.assertEqual(metricas["autorizados"], 1)
        self.assertEqual(metricas["pendentes"], 0)

        # Adiciona usuários
        self.usuario_repo.registrar_solicitacao(2001, "User 1", "u1")
        self.usuario_repo.registrar_solicitacao(2002, "User 2", "u2")
        self.usuario_repo.definir_autorizacao(2001, True)

        metricas = self.usuario_repo.obter_metricas()
        self.assertEqual(metricas["total"], 3)
        self.assertEqual(metricas["autorizados"], 2)
        self.assertEqual(metricas["pendentes"], 1)

    def test_metricas_alertas(self):
        a1 = Alerta(None, 1001, "BSB", "NAT", 800.0, "2026-10-10")
        a2 = Alerta(None, 1001, "BSB", "NAT", 750.0, "2026-11-10")
        a3 = Alerta(None, 2001, "GRU", "MIA", 2500.0, "2026-12-01")
        id1 = self.alerta_repo.salvar(a1)
        self.alerta_repo.salvar(a2)
        id3 = self.alerta_repo.salvar(a3)

        metricas = self.alerta_repo.obter_metricas()
        self.assertEqual(metricas["total_historico"], 3)
        self.assertEqual(metricas["ativos"], 3)
        self.assertEqual(len(metricas["top_trechos"]), 2)
        self.assertEqual(metricas["top_trechos"][0]["origem"], "BSB")
        self.assertEqual(metricas["top_trechos"][0]["destino"], "NAT")
        self.assertEqual(metricas["top_trechos"][0]["quantidade"], 2)

        # Desativa um alerta
        self.alerta_repo.desativar(id1, 1001)
        metricas2 = self.alerta_repo.obter_metricas()
        self.assertEqual(metricas2["total_historico"], 3)
        self.assertEqual(metricas2["ativos"], 2)

    def test_metricas_historico(self):
        self.historico_repo.registrar("BSB", "NAT", "2026-10-10", 650.0, "LATAM")
        self.historico_repo.registrar("BSB", "NAT", "2026-10-10", 620.0, "GOL")
        self.historico_repo.registrar("GRU", "MIA", "2026-12-01", 2100.0, "American")

        metricas = self.historico_repo.obter_metricas()
        self.assertEqual(metricas["total_cotacoes"], 3)
        self.assertEqual(metricas["trechos_unicos"], 2)

    def test_formatar_mensagem_painel_stats(self):
        u_stats = {"total": 10, "autorizados": 8, "pendentes": 2}
        a_stats = {
            "total_historico": 25,
            "ativos": 15,
            "top_trechos": [
                {"origem": "BSB", "destino": "NAT", "quantidade": 5},
                {"origem": "GRU", "destino": "MIA", "quantidade": 3}
            ]
        }
        h_stats = {"total_cotacoes": 1500, "trechos_unicos": 12}

        texto = NotifierService.mensagem_painel_stats(u_stats, a_stats, h_stats)
        self.assertIn("PAINEL DE ESTATÍSTICAS DO BOT", texto)
        self.assertIn("Total Geral: *10*", texto)
        self.assertIn("Alertas Ativos no Momento: *15*", texto)
        self.assertIn("Total de Cotações Registradas: *1.500*", texto)
        self.assertIn("`BSB` ➔ `NAT`: *5* alerta(s)", texto)

    async def test_stats_command_admin(self):
        update = MagicMock()
        update.effective_user.id = 1001
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
            "alerta_repo": self.alerta_repo,
            "historico_repo": self.historico_repo
        }

        await stats_command(update, context)
        update.message.reply_text.assert_called_once()
        texto_enviado = update.message.reply_text.call_args[0][0]
        self.assertIn("PAINEL DE ESTATÍSTICAS DO BOT", texto_enviado)

    async def test_admin_command_admin(self):
        update = MagicMock()
        update.effective_user.id = 1001
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": self.config}

        await admin_command(update, context)
        update.message.reply_text.assert_called_once()
        texto_enviado = update.message.reply_text.call_args[0][0]
        self.assertIn("CENTRAL DE CONTROLE DO ADMINISTRADOR", texto_enviado)

    async def test_stats_command_negado_nao_admin(self):
        update = MagicMock()
        update.effective_user.id = 9999
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {"config": self.config}

        await stats_command(update, context)
        update.message.reply_text.assert_called_once()
        texto_enviado = update.message.reply_text.call_args[0][0]
        self.assertIn("Comando restrito ao administrador", texto_enviado)
