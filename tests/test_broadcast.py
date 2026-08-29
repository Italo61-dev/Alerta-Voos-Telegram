import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.config import Config
from src.database.connection import DatabaseManager
from src.database.schema import init_db
from src.database.usuario_repository import UsuarioRepository
from src.models.usuario import Usuario
from src.services.broadcast_service import BroadcastService
from src.bot.handlers.admin_handlers import broadcast_command, broadcast_novidades_command
from src.bot.handlers.user_handlers import novidades_command

class TestBroadcast(unittest.IsolatedAsyncioTestCase):
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

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_listar_autorizados(self):
        self.usuario_repo.registrar_solicitacao(2001, "Alice", "alice")
        self.usuario_repo.registrar_solicitacao(2002, "Bob", "bob")
        self.usuario_repo.registrar_solicitacao(2003, "Charlie", "charlie")

        self.usuario_repo.definir_autorizacao(2001, True)
        self.usuario_repo.definir_autorizacao(2003, True)

        autorizados = self.usuario_repo.listar_autorizados()
        ids_autorizados = [u.user_id for u in autorizados]

        self.assertIn(1001, ids_autorizados)
        self.assertIn(2001, ids_autorizados)
        self.assertIn(2003, ids_autorizados)
        self.assertNotIn(2002, ids_autorizados)

    def test_formatar_mensagem_novidades(self):
        msg = BroadcastService.formatar_mensagem_novidades()
        self.assertIn("NOVIDADES NO BOT DE VOOS", msg)
        self.assertIn("Áudios de Voz com IA", msg)
        self.assertIn("Consultor Inteligente", msg)
        self.assertIn("Termômetro de Oportunidades", msg)
        self.assertIn("Filtro de Voos Diretos", msg)
        self.assertIn("Como usar:", msg)

    async def test_enviar_broadcast(self):
        bot_mock = MagicMock()
        bot_mock.send_message = AsyncMock()

        destinatarios = [
            Usuario(user_id=1, nome="User 1", username="u1", autorizado=True),
            Usuario(user_id=2, nome="User 2", username="u2", autorizado=True),
            Usuario(user_id=3, nome="User 3", username="u3", autorizado=True),
        ]

        async def side_effect(chat_id, text, **kwargs):
            if chat_id == 2:
                raise Exception("Blocked by user")
            return None

        bot_mock.send_message.side_effect = side_effect

        resultado = await BroadcastService.enviar_broadcast(
            bot=bot_mock,
            destinatarios=destinatarios,
            mensagem="Teste de Mensagem Global"
        )

        self.assertEqual(resultado["total"], 3)
        self.assertEqual(resultado["sucessos"], 2)
        self.assertEqual(resultado["falhas"], 1)
        self.assertEqual(bot_mock.send_message.await_count, 3)

    async def test_broadcast_command_admin(self):
        update = MagicMock()
        update.effective_user.id = 1001
        update.message.text = "/broadcast Promoção Relâmpago SP -> Salvador"
        status_mock = MagicMock()
        status_mock.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=status_mock)

        context = MagicMock()
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
        }
        context.bot.send_message = AsyncMock()

        await broadcast_command(update, context)

        update.message.reply_text.assert_called()
        status_mock.edit_text.assert_called()
        context.bot.send_message.assert_called()

    async def test_broadcast_novidades_command_admin(self):
        update = MagicMock()
        update.effective_user.id = 1001
        status_mock = MagicMock()
        status_mock.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=status_mock)

        context = MagicMock()
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
        }
        context.bot.send_message = AsyncMock()

        await broadcast_novidades_command(update, context)

        update.message.reply_text.assert_called()
        status_mock.edit_text.assert_called()
        context.bot.send_message.assert_called()

    async def test_novidades_command_user(self):
        update = MagicMock()
        update.effective_user.id = 1001
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "config": self.config,
            "usuario_repo": self.usuario_repo,
        }

        await novidades_command(update, context)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("NOVIDADES NO BOT DE VOOS", args[0])

if __name__ == "__main__":
    unittest.main()
