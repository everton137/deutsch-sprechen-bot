from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import openai
import asyncio
import tempfile

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        self.conversation_mode = "default"
        self.last_audio_response = None
        self.setup_handlers()

    def setup_handlers(self):
        """Set up command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Voice message handler
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        
        # Text message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! I can handle different conversation modes in German.\n"
            "Use special commands to switch modes:\n"
            "• 'Gesprächsmodus': Conversation mode (audio only)\n"
            "• 'Transkribieren': Transcribe last audio\n"
            "• 'Transkriptionsmodus': Return to default mode"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_text = """
Conversation Modes:
1. Default Mode: Full analysis of voice messages
   - Transcription
   - Translation
   - Key words

2. Gesprächsmodus (Conversation Mode):
   - Responds only with German audio
   - No text analysis

3. Transkriptionsmodus (Transcription Mode):
   - Returns to default full analysis mode

Special Commands:
- Say "Gesprächsmodus" to enter conversation mode
- Say "Transkribieren" to transcribe last audio
- Say "Transkriptionsmodus" to return to default mode
        """
        await update.message.reply_text(help_text)

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages."""
        try:
            # Send a processing message
            processing_message = await update.message.reply_text("Processing your voice message...")

            # Download the voice message
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            
            with tempfile.NamedTemporaryFile(suffix='.oga') as voice_temp:
                # Download voice file to temporary location
                await voice_file.download_to_drive(voice_temp.name)
                
                # Transcribe with Whisper
                with open(voice_temp.name, 'rb') as audio_file:
                    transcript = await self.transcribe_audio(audio_file)

            # Handle different conversation modes
            if self.conversation_mode == "default":
                await processing_message.delete()
                await self.handle_default_mode(update, transcript)
            elif self.conversation_mode == "conversation":
                await processing_message.delete()
                await self.handle_conversation_mode(update, transcript)
            elif self.conversation_mode == "transcription":
                await processing_message.delete()
                await self.handle_transcription_mode(update, transcript)

        except Exception as e:
            logger.error(f"Error processing voice message: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your voice message. "
                "Please try again later."
            )
            
    async def handle_default_mode(self, update: Update, transcript: str):
            """Full analysis mode with text and audio responses."""

            # Send a processing response message
            processing_response = await update.message.reply_text("Processing a response to you...")

            # Process the German text with GPT
            # understanding = await self.process_german_text(transcript)
            
            # Extract and translate key words
            word_translations = await self.extract_word_translations(transcript)
            
            # Generate German audio response
            german_response = await self.generate_german_response(transcript)
            audio_response = await self.generate_audio_response(german_response)
            
            # Store the audio response for potential transcription
            self.last_audio_response = audio_response

            await update.message.reply_text(
                f"📝 Frage Transkription:\n{transcript} \n\n"
            )
            
            await processing_response.delete()

            # Send audio response
            with tempfile.NamedTemporaryFile(suffix='.mp3') as audio_temp:
                audio_temp.write(audio_response)
                audio_temp.seek(0)
                await update.message.reply_voice(voice=audio_temp)

            # Extract and translate key words
            word_translations = await self.extract_word_translations(german_response)

             # Send german_respose
            await update.message.reply_text(
                f"📝 Antwort Transkription:\n{german_response} \n\n"
                f"💡 Understanding:\n{word_translations}\n\n"

            )
    async def transcribe_audio(self, audio_file):
        """Transcribe audio using OpenAI's Whisper API."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="de"
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            raise

    async def process_german_text(self, text):
        """Process German text using OpenAI's GPT model."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": (
                            "You are a helpful assistant processing German messages. "
                            "Analyze the content and provide a clear understanding "
                            "in English. Be concise but thorough."
                        )},
                        {"role": "user", "content": text}
                    ]
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in text processing: {str(e)}")
            raise

    async def generate_german_response(self, text):
        """Generate a German response to the input text."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": (
                            "You are a friendly German-speaking assistant. "
                            "Respond to the following message in natural, conversational German. "
                            "Keep your response concise and engaging, matching the tone of the input. "
                            "In case there are grammar mistakes, suggest an improvement with a correct version and explain it."
                        )},
                        {"role": "user", "content": text}
                    ]
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating German response: {str(e)}")
            raise

    async def generate_audio_response(self, text):
        """Generate audio response using OpenAI's TTS."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.audio.speech.create(
                    model="tts-1",
                    voice="echo",  # Can be alloy, echo, fable, onyx, nova, or shimmer
                    input=text
                )
            )
            return response.content
        except Exception as e:
            logger.error(f"Error generating audio response: {str(e)}")
            raise

    async def extract_word_translations(self, text):
        """Extract and translate key German words."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": (
                            "Extract the 3 most significant German words from the text. "
                            "For each word, provide: \n"
                            "- The German word\n"
                            "- Its English translation\n"
                            "- A brief context or explanation\n"
                            "Focus on nouns, verbs, and adjectives that carry key meaning. "
                            "Limit to 3 words maximum."
                        )},
                        {"role": "user", "content": text}
                    ]
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in word extraction: {str(e)}")
            raise
    async def handle_conversation_mode(self, update: Update, transcript: str):
        """Conversation mode - audio only response."""
        # Generate German audio response
        german_response = await self.generate_german_response(transcript)
        audio_response = await self.generate_audio_response(german_response)
        
        # Store the audio response for potential transcription
        self.last_audio_response = audio_response
        
        # Send audio response
        with tempfile.NamedTemporaryFile(suffix='.mp3') as audio_temp:
            audio_temp.write(audio_response)
            audio_temp.seek(0)
            await update.message.reply_voice(voice=audio_temp)
        
        print(german_response)
        # Send german_respose
        await update.message.reply_text(
            f"📝 Transkription:\n{german_response}"
        )

    async def handle_transcription_mode(self, update: Update, transcript: str):
        """Transcription mode - just transcribe the input."""
        await update.message.reply_text(
            f"📝 Transcription:\n{transcript}"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and mode switches."""
        text = update.message.text.lower().strip()
        
        if text == "gesprächsmodus":
            self.conversation_mode = "conversation"
            await update.message.reply_text(
                "🔊 Gesprächsmodus aktiviert. "
                "Ich werde jetzt nur mit Audioantworten kommunizieren."
            )
        elif text == "transkriptionsmodus":
            self.conversation_mode = "default"
            await update.message.reply_text(
                "📝 Zurück zum Standardmodus. "
                "Ich werde wieder vollständige Analysen durchführen."
            )
        elif text == "transkribieren":
            if self.last_audio_response:
                # Transcribe the last audio response
                with tempfile.NamedTemporaryFile(suffix='.mp3') as audio_temp:
                    audio_temp.write(self.last_audio_response)
                    audio_temp.seek(0)
                    with open(audio_temp.name, 'rb') as audio_file:
                        last_audio_transcript = await self.transcribe_audio(audio_file)
                
                await update.message.reply_text(
                    f"📝 Transkription der letzten Audioantwort:\n{last_audio_transcript}"
                )
            else:
                await update.message.reply_text(
                    "Es gibt noch keine vorherige Audioantwort zum Transkribieren."
                )
        else:
            # Default text message handling
            await update.message.reply_text(
                "Bitte senden Sie eine Sprachnachricht oder einen der Modus-Befehle.\n"
                "(/help für weitere Informationen)"
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log Errors caused by Updates."""
        logger.error(f"Exception while handling an update: {context.error}")

    def run(self):
        """Start the bot."""
        self.application.run_polling()

def main():
    # Get tokens from .env file
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not telegram_token or not openai_key:
        raise ValueError(
            "Missing required environment variables! "
            "Make sure both TELEGRAM_BOT_TOKEN and OPENAI_API_KEY are set in your .env file."
        )
    
    # Create and run bot
    bot = TelegramBot(telegram_token)
    bot.run()

if __name__ == '__main__':
    main()