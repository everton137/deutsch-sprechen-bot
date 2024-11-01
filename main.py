from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        """Initialize bot with Telegram token."""
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Set up command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("time", self.time_command))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! I'm your bot assistant.\n"
            "Use /help to see available commands."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/time - Show current time
        """
        await update.message.reply_text(help_text)

    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send current time when the command /time is issued."""
        current_time = datetime.now().strftime("%H:%M:%S")
        await update.message.reply_text(f"Current time is: {current_time}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo the user message."""
        await update.message.reply_text(f"You said: {update.message.text}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log Errors caused by Updates."""
        logger.error(f"Exception while handling an update: {context.error}")

    def run(self):
        """Start the bot."""
        self.application.run_polling()

def main():
    # Get token from .env file
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("No token found! Make sure TELEGRAM_BOT_TOKEN is set in your .env file.")
    
    # Create and run bot
    bot = TelegramBot(token)
    bot.run()

if __name__ == '__main__':
    main()