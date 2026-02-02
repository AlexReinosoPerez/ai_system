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
            "/help - Mostrar esta ayuda"
        )
        await update.message.reply_text(help_text)
    
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
