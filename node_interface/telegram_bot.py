"""
Telegram Bot Interface for AI System

This interface communicates with the system ONLY through the Router Contract.
It constructs ContractRequest objects and displays ContractResponse messages.
It never calls Router methods directly.
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from shared.config import config
from shared.logger import setup_logger
from node_interface.router import router
from node_interface.contract import Action, ContractRequest

logger = setup_logger(__name__, level=config.LOG_LEVEL)


def _make_request(
    action: Action,
    payload: dict = None,
    user_id: str = "unknown",
) -> ContractRequest:
    """Build a ContractRequest for dispatch to the Router."""
    return ContractRequest(
        action=action,
        payload=payload or {},
        source="telegram",
        user_id=str(user_id),
    )


class TelegramBot:
    """Telegram Bot handler — all commands go through Router Contract"""

    def __init__(self):
        """Initialize the bot"""
        config.validate()
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup command handlers"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("project", self.project_command))
        self.app.add_handler(CommandHandler("project_summary", self.project_summary_command))
        self.app.add_handler(CommandHandler("inbox", self.inbox_command))
        self.app.add_handler(CommandHandler("projects", self.projects_command))
        self.app.add_handler(CommandHandler("project_status", self.project_status_command))
        self.app.add_handler(CommandHandler("dds", self.dds_command))
        self.app.add_handler(CommandHandler("dds_new", self.dds_new_command))
        self.app.add_handler(CommandHandler("dds_approve", self.dds_approve_command))
        self.app.add_handler(CommandHandler("dds_reject", self.dds_reject_command))
        self.app.add_handler(CommandHandler("execute", self.execute_command))
        self.app.add_handler(CommandHandler("exec_status", self.exec_status_command))
        self.app.add_handler(CommandHandler("todo_list", self.todo_list_command))
        self.app.add_handler(CommandHandler("todo_to_dds", self.todo_to_dds_command))
        self.app.add_handler(CommandHandler("dds_list_proposed", self.dds_list_proposed_command))

    # ──────────────────────────────────────────────
    # LOCAL-ONLY commands (not routed through contract)
    # These are pure UI concerns with no system interaction.
    # ──────────────────────────────────────────────

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Command /start received from user {update.effective_user.id}")
        await update.message.reply_text(
            "🤖 AI System Online\n\n"
            "Sistema modular de inteligencia artificial.\n\n"
            "Usa /help para ver los comandos disponibles."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        logger.info(f"Command /help received from user {update.effective_user.id}")
        help_text = (
            "📋 Comandos disponibles:\n\n"
            "/start - Iniciar el bot\n"
            "/status - Ver estado del sistema\n"
            "/project <nombre> - Ver info de proyecto\n"
            "/project_summary <nombre> - Ver resumen del proyecto\n"
            "/inbox [cantidad] - Ver correos recientes\n"
            "/projects - Listar proyectos registrados\n"
            "/project_status <nombre> - Ver estado de proyecto\n"
            "/dds - Listar propuestas DDS\n"
            "/dds_new <proyecto> <título> <descripción>\n"
            "/dds_approve <id> - Aprobar propuesta\n"
            "/dds_reject <id> - Rechazar propuesta\n"
            "/execute <dds_id> - Ejecutar DDS aprobado\n"
            "/exec_status - Ver última ejecución\n"
            "/todo_list - Listar todos los ToDos\n"
            "/todo_to_dds <todo_id> - Generar DDS desde ToDo\n"
            "/dds_list_proposed - Listar DDS propuestos\n"
            "/help - Mostrar esta ayuda"
        )
        await update.message.reply_text(help_text)

    # ──────────────────────────────────────────────
    # CONTRACT-ROUTED commands
    # Each handler builds a ContractRequest → dispatches → shows response.message
    # ──────────────────────────────────────────────

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        logger.info(f"Command /status received from user {update.effective_user.id}")
        request = _make_request(Action.SYSTEM_STATUS, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def project_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project command"""
        logger.info(f"Command /project received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project <nombre>\n\n"
                "Ejemplo: /project fitnessai"
            )
            return

        request = _make_request(
            Action.PROJECT_INFO,
            payload={"name": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def project_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project_summary command"""
        logger.info(f"Command /project_summary received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project_summary <nombre>\n\n"
                "Ejemplo: /project_summary fitnessai"
            )
            return

        request = _make_request(
            Action.PROJECT_SUMMARY,
            payload={"name": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def inbox_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /inbox command"""
        logger.info(f"Command /inbox received from user {update.effective_user.id}")

        count = 10
        if context.args:
            try:
                count = int(context.args[0])
                if count < 1 or count > 50:
                    await update.message.reply_text(
                        "⚠️ La cantidad debe estar entre 1 y 50"
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Uso: /inbox [cantidad]\n\n"
                    "Ejemplo: /inbox 20"
                )
                return

        request = _make_request(
            Action.INBOX,
            payload={"count": count},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def projects_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /projects command"""
        logger.info(f"Command /projects received from user {update.effective_user.id}")
        request = _make_request(Action.PROJECT_LIST, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def project_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project_status command"""
        logger.info(f"Command /project_status received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project_status <nombre>\n\n"
                "Ejemplo: /project_status fitnessai"
            )
            return

        request = _make_request(
            Action.PROJECT_STATUS,
            payload={"name": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def dds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds command"""
        logger.info(f"Command /dds received from user {update.effective_user.id}")
        request = _make_request(Action.DDS_LIST, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def dds_new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_new command"""
        logger.info(f"Command /dds_new received from user {update.effective_user.id}")

        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ Uso: /dds_new <proyecto> <título> <descripción>\n\n"
                "Ejemplo: /dds_new fitnessai \"Nueva feature\" \"Descripción detallada\""
            )
            return

        request = _make_request(
            Action.DDS_NEW,
            payload={
                "project": context.args[0],
                "title": context.args[1],
                "description": " ".join(context.args[2:]),
            },
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def dds_approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_approve command"""
        logger.info(f"Command /dds_approve received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /dds_approve <id>\n\n"
                "Ejemplo: /dds_approve DDS-20260202123456"
            )
            return

        request = _make_request(
            Action.DDS_APPROVE,
            payload={"proposal_id": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def dds_reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_reject command"""
        logger.info(f"Command /dds_reject received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /dds_reject <id>\n\n"
                "Ejemplo: /dds_reject DDS-20260202123456"
            )
            return

        request = _make_request(
            Action.DDS_REJECT,
            payload={"proposal_id": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /execute command"""
        logger.info(f"Command /execute received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /execute <dds_id>\n\n"
                "Ejemplo: /execute DDS-20260202123456"
            )
            return

        request = _make_request(
            Action.EXECUTE,
            payload={"dds_id": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def exec_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exec_status command"""
        logger.info(f"Command /exec_status received from user {update.effective_user.id}")
        request = _make_request(Action.EXEC_STATUS, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def todo_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /todo_list command"""
        logger.info(f"Command /todo_list received from user {update.effective_user.id}")
        request = _make_request(Action.TODO_LIST, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def todo_to_dds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /todo_to_dds command"""
        logger.info(f"Command /todo_to_dds received from user {update.effective_user.id}")

        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /todo_to_dds <TODO-ID>\n\n"
                "Ejemplo: /todo_to_dds TODO-20260202-001"
            )
            return

        request = _make_request(
            Action.TODO_TO_DDS,
            payload={"todo_id": context.args[0]},
            user_id=update.effective_user.id,
        )
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    async def dds_list_proposed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_list_proposed command"""
        logger.info(f"Command /dds_list_proposed received from user {update.effective_user.id}")
        request = _make_request(Action.DDS_LIST_PROPOSED, user_id=update.effective_user.id)
        response = router.dispatch(request)
        await update.message.reply_text(response.message)

    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Bot with polling...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Telegram Bot stopped")


def main():
    """Main entry point"""
    logger.info("Initializing AI System - Node A (Interface)")
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
