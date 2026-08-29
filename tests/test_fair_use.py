import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler
from src.config import Config
from src.database.connection import DatabaseManager
from src.database.schema import init_db
from src.database.alerta_repository import AlertaRepository
from src.database.usuario_repository import UsuarioRepository
from src.models.alerta import Alerta
from src.services.notifier_service import NotifierService
from src.bot.handlers.user_handlers import alerta_command
from src.bot.handlers.wizard_handlers import iniciar_wizard
from src.services.travel_agent import TravelAgent

class TestFairUse(unittest.IsolatedAsyncioTestCase):
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
            db_path=Path(self.temp_db.name),
            max_alertas_por_usuario=10
        )
        self.db_manager = DatabaseManager(self.config)
        init_db(self.config)
        self.usuario_repo = UsuarioRepository(self.db_manager)
        self.alerta_repo = AlertaRepository(self.db_manager)

        # Autoriza usuário 2001 para testes
        self.usuario_repo.registrar_solicitacao(2001, "User Teste", "userteste")
        self.usuario_repo.definir_autorizacao(2001, True)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_contar_ativos_por_usuario(self):
        user_id = 2001
        self.assertEqual(self.alerta_repo.contar_ativos_por_usuario(user_id), 0)

        for i in range(3):
            self.alerta_repo.salvar(Alerta(None, user_id, "BSB", "NAT", 500.0 + i, "2026-10-15"))

        self.assertEqual(self.alerta_repo.contar_ativos_por_usuario(user_id), 3)

        # Desativa um
        alertas = self.alerta_repo.listar_por_usuario(user_id)
        self.alerta_repo.desativar(alertas[0].id, user_id)
        self.assertEqual(self.alerta_repo.contar_ativos_por_usuario(user_id), 2)

    async def test_alerta_command_bloqueia_quando_atinge_limite(self):
        user_id = 2001
        for i in range(10):
            self.alerta_repo.salvar(Alerta(None, user_id, "BSB", "NAT", 500.0 + i, f"2026-10-{15+i}"))

        update = MagicMock()
        update.effective_chat.id = user_id
        update.effective_user.id = user_id
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["BSB", "NAT", "800", "2026-11-20"]
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
            "alerta_repo": self.alerta_repo
        }

        await alerta_command(update, context)
        update.message.reply_text.assert_called_once()
        texto = update.message.reply_text.call_args[0][0]
        self.assertIn("Limite de Alertas Atingido", texto)
        self.assertIn("10 alertas ativos simultâneos", texto)

    async def test_alerta_command_admin_ilimitado(self):
        admin_id = 1001
        for i in range(12):
            self.alerta_repo.salvar(Alerta(None, admin_id, "BSB", "NAT", 500.0 + i, f"2026-10-15"))

        update = MagicMock()
        update.effective_chat.id = admin_id
        update.effective_user.id = admin_id
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["BSB", "NAT", "800", "2026-11-20"]
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
            "alerta_repo": self.alerta_repo
        }

        await alerta_command(update, context)
        update.message.reply_text.assert_called_once()
        texto = update.message.reply_text.call_args[0][0]
        # Admin não é bloqueado por limite
        self.assertNotIn("Limite de Alertas Atingido", texto)
        self.assertIn("cadastrado com sucesso", texto)

    async def test_iniciar_wizard_bloqueia_usuario_no_limite(self):
        user_id = 2001
        for i in range(10):
            self.alerta_repo.salvar(Alerta(None, user_id, "BSB", "NAT", 500.0 + i, f"2026-10-{15+i}"))

        update = MagicMock()
        update.effective_user.id = user_id
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
            "alerta_repo": self.alerta_repo
        }
        context.user_data = {}

        res = await iniciar_wizard(update, context)
        self.assertEqual(res, ConversationHandler.END)
        update.message.reply_text.assert_called_once()
        texto = update.message.reply_text.call_args[0][0]
        self.assertIn("Limite de Alertas Atingido", texto)

    def test_travel_agent_bloqueia_cadastro_no_limite(self):
        user_id = 2001
        for i in range(10):
            self.alerta_repo.salvar(Alerta(None, user_id, "BSB", "NAT", 500.0 + i, f"2026-10-{15+i}"))

        mock_client = MagicMock()
        agent = TravelAgent(
            client=mock_client,
            user_id=user_id,
            alerta_repo=self.alerta_repo,
            max_alertas=10,
            admin_id=1001
        )

        self.assertEqual(self.alerta_repo.contar_ativos_por_usuario(user_id), 10)
