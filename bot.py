import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import DeepLTranslator
import os
from dotenv import load_dotenv
import logging

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEEPL_KEY = os.getenv("DEEPL_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translate_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Die wichtigsten Flaggen
FLAG_LANGUAGES = {
    "🇩🇪": "de",
    "🇬🇧": "en",
    "🇺🇸": "en",
    "🇫🇷": "fr",
    "🇪🇸": "es",
    "🇮🇹": "it",
    "🇵🇹": "pt",
    "🇷🇺": "ru",
    "🇯🇵": "ja",
    "🇰🇷": "ko",
    "🇨🇳": "zh",
    "🇳🇱": "nl",
    "🇵🇱": "pl",
    "🇹🇷": "tr",
    "🇺🇦": "uk",
    "🇸🇦": "ar",
}

def translate_text(text: str, target: str) -> str:
    try:
        translator = DeepLTranslator(
            api_key=DEEPL_KEY,
            source="auto",
            target=target.lower()
        )
        return translator.translate(text)
    except Exception as e:
        logger.error(f"DeepL Fehler: {e}")
        return f"Übersetzungsfehler: {e}"

# ======================
# Slash Command
# ======================
@bot.tree.command(name="translate", description="Übersetzt einen Text")
@app_commands.describe(
    text="Der Text, der übersetzt werden soll",
    target="Zielsprache (z.B. de, en, fr, es, ja)"
)
async def translate(interaction: discord.Interaction, text: str, target: str = "de"):
    await interaction.response.defer(ephemeral=True)
    translated = translate_text(text, target)
    await interaction.followup.send(translated, ephemeral=True)

# ======================
# Context Menus
# ======================
@bot.tree.context_menu(name="Übersetzen (DE)")
async def translate_to_german(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if not message.content:
        await interaction.followup.send("Diese Nachricht hat keinen Text.", ephemeral=True)
        return
    translated = translate_text(message.content, "de")
    await interaction.followup.send(translated, ephemeral=True)

@bot.tree.context_menu(name="Translate to English")
async def translate_to_english(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if not message.content:
        await interaction.followup.send("This message has no text.", ephemeral=True)
        return
    translated = translate_text(message.content, "en")
    await interaction.followup.send(translated, ephemeral=True)

# ======================
# Flaggen-Reaktion → private DM
# ======================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in FLAG_LANGUAGES:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return

    if not message.content:
        return

    lang = FLAG_LANGUAGES[emoji]

    try:
        user = await bot.fetch_user(payload.user_id)
        translated = translate_text(message.content, lang)

        try:
            await user.send(
                f"**Übersetzung ({lang.upper()})**\n"
                f"Original: {message.jump_url}\n\n"
                f"{translated}"
            )
        except discord.Forbidden:
            logger.warning(f"Konnte DM an {user} nicht senden (DMs deaktiviert)")

    except Exception as e:
        logger.error(f"Flaggen-Übersetzung fehlgeschlagen: {e}")

# ======================
# Ready
# ======================
@bot.event
async def on_ready():
    logger.info(f"Bot ist online als {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"{len(synced)} Commands synchronisiert")
    except Exception as e:
        logger.error(f"Sync-Fehler: {e}")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")
if not DEEPL_KEY:
    raise RuntimeError("DEEPL_API_KEY fehlt!")

bot.run(TOKEN)
