"""
Telegram Bot Interface for AI System
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from shared.config import config
from shared.logger import setup_logger
from node_interface.router import router

logger = setup_logger(__name__, level=config.LOG_LEVEL)


class TelegramBot:
    """Telegram Bot handler"""
    
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Command /start received from user {update.effective_user.id}")
        await update.message.reply_text(
            "🤖 AI System Online\n\n"
            "Sistema modular de inteligencia artificial.\n\n"
            "Usa /help para ver los comandos disponibles."
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        logger.info(f"Command /status received from user {update.effective_user.id}")
        status = router.get_system_status()
        await update.message.reply_text(status)
    
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
            "/help - Mostrar esta ayuda"
        )
        await update.message.reply_text(help_text)
    
    async def project_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project command"""
        logger.info(f"Command /project received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project <nombre>\n\n"
                "Ejemplo: /project fitnessai"
            )
            return
        
        project_name = context.args[0]
        result = router.project(project_name)
        await update.message.reply_text(result)
    
    async def project_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project_summary command"""
        logger.info(f"Command /project_summary received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project_summary <nombre>\n\n"
                "Ejemplo: /project_summary fitnessai"
            )
            return
        
        project_name = context.args[0]
        result = router.project_summary(project_name)
        await update.message.reply_text(result)
    
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
        
        result = router.inbox(count)
        await update.message.reply_text(result)
    
    async def projects_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /projects command"""
        logger.info(f"Command /projects received from user {update.effective_user.id}")
        result = router.projects()
        await update.message.reply_text(result)
    
    async def project_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /project_status command"""
        logger.info(f"Command /project_status received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /project_status <nombre>\n\n"
                "Ejemplo: /project_status fitnessai"
            )
            return
        
        project_name = context.args[0]
        result = router.project_status(project_name)
        await update.message.reply_text(result)
    
    async def dds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds command"""
        logger.info(f"Command /dds received from user {update.effective_user.id}")
        result = router.dds_list()
        await update.message.reply_text(result)
    
    async def dds_new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_new command"""
        logger.info(f"Command /dds_new received from user {update.effective_user.id}")
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "⚠️ Uso: /dds_new <proyecto> <título> <descripción>\n\n"
                "Ejemplo: /dds_new fitnessai \"Nueva feature\" \"Descripción detallada\""
            )
            return
        
        project = context.args[0]
        title = context.args[1]
        description = ' '.join(context.args[2:])
        
        result = router.dds_new(project, title, description)
        await update.message.reply_text(result)
    
    async def dds_approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_approve command"""
        logger.info(f"Command /dds_approve received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /dds_approve <id>\n\n"
                "Ejemplo: /dds_approve DDS-20260202123456"
            )
            return
        
        proposal_id = context.args[0]
        result = router.dds_approve(proposal_id)
        await update.message.reply_text(result)
    
    async def dds_reject_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dds_reject command"""
        logger.info(f"Command /dds_reject received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /dds_reject <id>\n\n"
                "Ejemplo: /dds_reject DDS-20260202123456"
            )
            return
        
        proposal_id = context.args[0]
        result = router.dds_reject(proposal_id)
        await update.message.reply_text(result)
    
    async def execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /execute command"""
        logger.info(f"Command /execute received from user {update.effective_user.id}")
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Uso: /execute <dds_id>\n\n"
                "Ejemplo: /execute DDS-20260202123456"
            )
            return
        
        dds_id = context.args[0]
        result = router.execute(dds_id)
        await update.message.reply_text(result)
    
    async def exec_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exec_status command"""
        logger.info(f"Command /exec_status received from user {update.effective_user.id}")
        result = router.exec_status()
        await update.message.reply_text(result)
    
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
