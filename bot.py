import asyncio
import logging
import os
import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import DeepLTranslator
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEEPL_KEY = os.getenv("DEEPL_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translate_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Flagge → Sprachcode
FLAG_LANGUAGES = {
    "🇩🇪": "de", "🇦🇹": "de", "🇱🇮": "de",
    "🇬🇧": "en", "🇺🇸": "en", "🇨🇦": "en", "🇦🇺": "en",
    "🇫🇷": "fr", "🇧🇪": "fr", "🇨🇭": "fr",
    "🇪🇸": "es", "🇲🇽": "es", "🇦🇷": "es", "🇨🇴": "es",
    "🇮🇹": "it", "🇵🇹": "pt", "🇧🇷": "pt",
    "🇷🇺": "ru", "🇺🇦": "uk", "🇵🇱": "pl",
    "🇨🇿": "cs", "🇸🇰": "sk", "🇸🇮": "sl", "🇭🇷": "hr",
    "🇧🇬": "bg", "🇷🇴": "ro", "🇭🇺": "hu",
    "🇳🇱": "nl", "🇩🇰": "da", "🇸🇪": "sv", "🇳🇴": "nb", "🇫🇮": "fi",
    "🇪🇪": "et", "🇱🇻": "lv", "🇱🇹": "lt", "🇬🇷": "el",
    "🇹🇷": "tr", "🇯🇵": "ja", "🇰🇷": "ko", "🇨🇳": "zh",
    "🇸🇦": "ar", "🇮🇱": "he", "🇮🇳": "hi", "🇮🇩": "id",
    "🇻🇳": "vi", "🇹🇭": "th", "🇺🇦": "uk",
}

LANGUAGE_NAMES = {
    "de": "Deutsch", "en": "Englisch", "fr": "Französisch", "es": "Spanisch",
    "it": "Italienisch", "pt": "Portugiesisch", "ru": "Russisch", "ja": "Japanisch",
    "ko": "Koreanisch", "zh": "Chinesisch", "nl": "Niederländisch", "pl": "Polnisch",
    "tr": "Türkisch", "ar": "Arabisch", "uk": "Ukrainisch", "cs": "Tschechisch",
    "sk": "Slowakisch", "sl": "Slowenisch", "hr": "Kroatisch", "bg": "Bulgarisch",
    "ro": "Rumänisch", "hu": "Ungarisch", "da": "Dänisch", "sv": "Schwedisch",
    "nb": "Norwegisch", "fi": "Finnisch", "et": "Estnisch", "lv": "Lettisch",
    "lt": "Litauisch", "el": "Griechisch", "he": "Hebräisch", "hi": "Hindi",
    "id": "Indonesisch", "vi": "Vietnamesisch", "th": "Thailändisch",
}

LANGUAGE_PAGE_SIZE = 20

async def translate_text(text: str, target: str) -> str:
    """Übersetzt mit DeepL (im Thread, damit Discord nicht blockiert)."""
    def _translate():
        translator = DeepLTranslator(
            api_key=DEEPL_KEY,
            source="auto",
            target=target.lower()
        )
        return translator.translate(text)

    return await asyncio.to_thread(_translate)

def split_message(text: str, limit: int = 2000) -> list[str]:
    parts = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        parts.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        parts.append(remaining)
    return parts or ["(Keine Übersetzung verfügbar.)"]

# ======================
# Slash Command
# ======================
@bot.tree.command(name="translate", description="Übersetzt einen Text")
@app_commands.describe(
    text="Der Text, der übersetzt werden soll",
    target="Zielsprache (z. B. de, en, fr, es, ja)",
)
async def translate(interaction: discord.Interaction, text: str, target: str = "de"):
    await interaction.response.defer(ephemeral=True)
    try:
        translated = await translate_text(text, target.lower())
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as error:
        await interaction.followup.send(f"Fehler: `{error}`", ephemeral=True)

# ======================
# Context Menus
# ======================
@bot.tree.context_menu(name="Übersetzen (DE)")
async def translate_to_german(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if not message.content:
        await interaction.followup.send("Diese Nachricht hat keinen Text.", ephemeral=True)
        return
    try:
        translated = await translate_text(message.content, "de")
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as error:
        await interaction.followup.send(f"Fehler: `{error}`", ephemeral=True)

@bot.tree.context_menu(name="Translate to English")
async def translate_to_english(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if not message.content:
        await interaction.followup.send("This message has no text.", ephemeral=True)
        return
    try:
        translated = await translate_text(message.content, "en")
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as error:
        await interaction.followup.send(f"Error: `{error}`", ephemeral=True)

# ======================
# Flaggen-Buttons (private)
# ======================
class TranslationButton(discord.ui.Button):
    def __init__(self, emoji: str, target_language: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=LANGUAGE_NAMES.get(target_language, target_language.upper()),
            # Wichtig: keine Emoji mehr in der custom_id
            custom_id=f"translate_{target_language}_{hash(emoji) % 10000}",
        )
        self.target_language = target_language

    async def callback(self, interaction: discord.Interaction) -> None:
        source_message = self.view.source_message

        if not source_message or not source_message.content:
            await interaction.response.send_message(
                "Diese Nachricht hat keinen Text.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            translated = await translate_text(source_message.content, self.target_language)
            language = LANGUAGE_NAMES.get(self.target_language, self.target_language.upper())

            await interaction.followup.send(
                f"**Übersetzung: {language}**\nQuelle: {source_message.jump_url}",
                ephemeral=True,
            )
            for part in split_message(translated):
                await interaction.followup.send(part, ephemeral=True)

        except Exception as error:
            logger.exception("Button-Übersetzung fehlgeschlagen")
            await interaction.followup.send(
                f"❌ Fehler bei der Übersetzung:\n```{error}```",
                ephemeral=True
            )

class PageButton(discord.ui.Button):
    def __init__(self, direction: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="◀ Zurück" if direction < 0 else "Weiter ▶",
            row=4,
        )
        self.direction = direction

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if view is None:
            return
        new_page = max(0, min(view.page + self.direction, view.page_count - 1))
        await interaction.response.edit_message(
            content=view.page_text(new_page),
            view=TranslationView(view.source_message, new_page),
        )

class TranslationView(discord.ui.View):
    def __init__(self, source_message: discord.Message, page: int = 0):
        super().__init__(timeout=None)
        self.source_message = source_message
        self.page = page
        self.language_items = list(FLAG_LANGUAGES.items())
        self.page_count = (len(self.language_items) + LANGUAGE_PAGE_SIZE - 1) // LANGUAGE_PAGE_SIZE

        start = page * LANGUAGE_PAGE_SIZE
        for emoji, target_language in self.language_items[start : start + LANGUAGE_PAGE_SIZE]:
            self.add_item(TranslationButton(emoji, target_language))

        if page > 0:
            self.add_item(PageButton(-1))
        if page < self.page_count - 1:
            self.add_item(PageButton(1))

    def page_text(self, page: int) -> str:
        return (
            f"Wähle eine Flagge für die gewünschte Sprache. "
            f"Seite {page + 1}/{self.page_count}. Die Übersetzung wird nur dir angezeigt."
        )

@bot.tree.context_menu(name="Flaggen-Übersetzung")
async def add_translation_buttons(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        await interaction.response.send_message("Diese Nachricht hat keinen Text.", ephemeral=True)
        return

    view = TranslationView(message)
    await interaction.response.send_message(
        content=view.page_text(0),
        view=view,
        ephemeral=True,
    )

# ======================
# Ready
# ======================
@bot.event
async def on_ready():
    logger.info("Bot ist online als %s", bot.user)
    try:
        synced = await bot.tree.sync()
        logger.info("%s Commands synchronisiert", len(synced))
    except discord.HTTPException as error:
        logger.warning("Sync-Fehler: %s", error)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt!")
if not DEEPL_KEY:
    raise RuntimeError("DEEPL_API_KEY fehlt!")

bot.run(TOKEN)
