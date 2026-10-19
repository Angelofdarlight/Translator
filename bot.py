import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import MyMemoryTranslator
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translate_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Flagge → Sprachcode. Die Flagge steht jeweils stellvertretend für die Sprache.
# Google Translate unterstützt zusätzlich regionale beziehungsweise alternative
# Sprachvarianten; bei identischen Sprachen können mehrere Flaggen verwendet werden.
FLAG_LANGUAGES = {
    "🇩🇪": "de", "🇦🇹": "de", "🇱🇮": "de",
    "🇬🇧": "en", "🇺🇸": "en", "🇨🇦": "en", "🇦🇺": "en",
    "🇫🇷": "fr", "🇧🇪": "fr", "🇨🇭": "fr",
    "🇪🇸": "es", "🇲🇽": "es", "🇦🇷": "es", "🇨🇴": "es",
    "🇮🇹": "it", "🇵🇹": "pt", "🇧🇷": "pt",
    "🇷🇺": "ru", "🇧🇾": "be", "🇺🇦": "uk", "🇵🇱": "pl",
    "🇨🇿": "cs", "🇸🇰": "sk", "🇸🇮": "sl", "🇭🇷": "hr", "🇷🇸": "sr",
    "🇧🇦": "bs", "🇧🇬": "bg", "🇲🇰": "mk", "🇷🇴": "ro", "🇭🇺": "hu",
    "🇳🇱": "nl", "🇩🇰": "da", "🇸🇪": "sv", "🇳🇴": "no", "🇫🇮": "fi",
    "🇮🇸": "is", "🇪🇪": "et", "🇱🇻": "lv", "🇱🇹": "lt", "🇬🇷": "el",
    "🇹🇷": "tr", "🇦🇱": "sq", "🇦🇲": "hy", "🇬🇪": "ka", "🇦🇿": "az",
    "🇮🇱": "iw", "🇮🇷": "fa", "🇦🇫": "ps", "🇮🇳": "hi", "🇵🇰": "ur",
    "🇧🇩": "bn", "🇳🇵": "ne", "🇱🇰": "si", "🇮🇩": "id", "🇲🇾": "ms",
    "🇵🇭": "tl", "🇻🇳": "vi", "🇹🇭": "th", "🇰🇭": "km", "🇱🇦": "lo",
    "🇲🇲": "my", "🇨🇳": "zh-CN", "🇹🇼": "zh-TW", "🇯🇵": "ja", "🇰🇷": "ko",
    "🇲🇳": "mn", "🇰🇿": "kk", "🇺🇿": "uz", "🇰🇬": "ky", "🇹🇯": "tg",
    "🇸🇦": "ar", "🇪🇬": "ar", "🇮🇶": "ar",
    "🇸🇴": "so", "🇸🇩": "sd", "🇸🇳": "wo", "🇰🇪": "sw", "🇿🇼": "sn",
    "🇪🇹": "am", "🇲🇬": "mg", "🇲🇼": "ny", "🇿🇲": "bem", "🇷🇼": "rw", "🇳🇦": "af",
    "🇳🇿": "mi", "🇼🇸": "sm", "🇮🇪": "ga", "🏴": "cy", "🇿🇦": "zu",
    "🇲🇱": "bm", "🇭🇹": "ht", "🇱🇺": "lb", "🇲🇹": "mt", "🇸🇬": "ms",
    "🇱🇾": "ar", "🇧🇭": "ar", "🇴🇲": "ar", "🇶🇦": "ar", "🇦🇪": "ar",
}

LANGUAGE_NAMES = {
    "de": "Deutsch", "en": "Englisch", "fr": "Französisch", "es": "Spanisch",
    "it": "Italienisch", "pt": "Portugiesisch", "ru": "Russisch", "ja": "Japanisch",
    "ko": "Koreanisch", "zh-CN": "Chinesisch (vereinfacht)", "zh-TW": "Chinesisch (traditionell)",
    "nl": "Niederländisch", "pl": "Polnisch", "tr": "Türkisch", "ar": "Arabisch",
    "uk": "Ukrainisch", "be": "Belarussisch", "cs": "Tschechisch", "sk": "Slowakisch",
    "sl": "Slowenisch", "hr": "Kroatisch", "sr": "Serbisch", "bs": "Bosnisch",
    "bg": "Bulgarisch", "mk": "Mazedonisch", "ro": "Rumänisch", "hu": "Ungarisch",
    "da": "Dänisch", "sv": "Schwedisch", "no": "Norwegisch", "fi": "Finnisch",
    "is": "Isländisch", "et": "Estnisch", "lv": "Lettisch", "lt": "Litauisch",
    "el": "Griechisch", "sq": "Albanisch", "hy": "Armenisch", "ka": "Georgisch",
    "az": "Aserbaidschanisch", "iw": "Hebräisch", "fa": "Persisch", "ps": "Paschtu",
    "hi": "Hindi", "ur": "Urdu", "bn": "Bengalisch", "ne": "Nepali", "si": "Singhalesisch",
    "id": "Indonesisch", "ms": "Malaiisch", "tl": "Filipino", "vi": "Vietnamesisch",
    "th": "Thailändisch", "km": "Khmer", "lo": "Laotisch", "my": "Birmanisch",
    "mn": "Mongolisch", "kk": "Kasachisch", "uz": "Usbekisch", "ky": "Kirgisisch",
    "tg": "Tadschikisch", "af": "Afrikaans", "so": "Somali", "sd": "Sindhi",
    "wo": "Wolof", "sw": "Suaheli", "sn": "Shona", "am": "Amharisch", "mg": "Malagasy",
    "ny": "Chichewa", "bem": "Bemba", "rw": "Kinyarwanda", "mi": "Māori", "sm": "Samoanisch",
    "ga": "Irisch", "cy": "Walisisch", "zu": "Zulu", "bm": "Bambara", "ht": "Haitianisches Kreol",
    "lb": "Luxemburgisch", "mt": "Maltesisch",
}

# Discord erlaubt höchstens fünf Buttons pro Action Row und fünf Rows pro Nachricht.
# Deshalb wird die große Sprachliste in Seiten mit maximal 20 Sprachbuttons geteilt.
LANGUAGE_PAGE_SIZE = 20


async def translate_text(text: str, target: str) -> str:
    """Führt die synchrone Übersetzung aus, ohne den Discord-Event-Loop zu blockieren."""
    return await asyncio.to_thread(
        MyMemoryTranslator(source="auto", target=target).translate, text
    )


def split_message(text: str, limit: int = 2_000) -> list[str]:
    """Teilt lange Übersetzungen möglichst an Zeilen- oder Wortgrenzen."""
    parts: list[str] = []
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


async def send_private_translation(
    user: discord.abc.User,
    source_message: discord.Message,
    translated: str,
    target: str,
) -> None:
    """Sendet das Übersetzungsergebnis ausschließlich als private Direktnachricht."""
    language = LANGUAGE_NAMES.get(target, target.upper())

    # Eine Reaktion ist keine Interaction. Daher ist eine Ephemeral-Nachricht
    # technisch nicht möglich; die private Direktnachricht ist die sichere Alternative.
    await user.send(
        f"**Übersetzung: {language}**\n"
        f"Quelle: {source_message.jump_url}\n"
        "Diese Übersetzung ist nur für dich sichtbar."
    )

    for part in split_message(translated):
        await user.send(part)


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
# Context Menu
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
# Flaggen-Buttons
# ======================
class TranslationButton(discord.ui.Button):
    """Ein Button für eine Zielsprache."""

    def __init__(self, emoji: str, target_language: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=LANGUAGE_NAMES.get(target_language, target_language.upper()),
            # Die Flagge ist Teil der ID, damit Englisch über 🇬🇧 und 🇺🇸
            # zwei technisch eindeutige Buttons erzeugt.
            custom_id=f"translate:{emoji}",
        )
        self.target_language = target_language

    async def callback(self, interaction: discord.Interaction) -> None:
        source_message = self.view.source_message  # type: ignore[union-attr]

        if not source_message.content:
            await interaction.response.send_message(
                "Diese Nachricht hat keinen Text.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            translated = await translate_text(
                source_message.content, self.target_language
            )
            language = LANGUAGE_NAMES.get(
                self.target_language, self.target_language.upper()
            )
            await interaction.followup.send(
                f"**Übersetzung: {language}**\n"
                f"Quelle: {source_message.jump_url}",
                ephemeral=True,
            )

            # Discord-Nachrichten sind begrenzt. Alle Übersetzungsteile bleiben
            # ebenfalls ephemer und sind nur für die klickende Person sichtbar.
            for part in split_message(translated):
                await interaction.followup.send(part, ephemeral=True)
        except Exception as error:
            logger.exception("Button-Übersetzung fehlgeschlagen: %s", error)
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Fehler bei der Übersetzung: `{error}`", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Fehler bei der Übersetzung: `{error}`", ephemeral=True
                )


class PageButton(discord.ui.Button):
    """Navigationsbutton für die Flaggen-Seiten."""

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
    """Enthält eine Seite der Flaggen-Buttons für eine konkrete Nachricht."""

    def __init__(self, source_message: discord.Message, page: int = 0):
        super().__init__(timeout=None)
        self.source_message = source_message
        self.page = page
        self.language_items = list(FLAG_LANGUAGES.items())
        self.page_count = (
            len(self.language_items) + LANGUAGE_PAGE_SIZE - 1
        ) // LANGUAGE_PAGE_SIZE

        start = page * LANGUAGE_PAGE_SIZE
        for emoji, target_language in self.language_items[
            start : start + LANGUAGE_PAGE_SIZE
        ]:
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
async def add_translation_buttons(
    interaction: discord.Interaction, message: discord.Message
):
    """Postet die Flaggen-Buttons als Antwort auf eine Nachricht."""
    if not message.content:
        await interaction.response.send_message(
            "Diese Nachricht hat keinen Text.", ephemeral=True
        )
        return

    view = TranslationView(message)
    await interaction.response.send_message(
        view=view,
        content=view.page_text(0),
        ephemeral=True,
    )


@bot.tree.command(
    name="translate_buttons",
    description="Zeigt private Flaggen-Buttons für eine Nachricht an",
)
async def translate_buttons(interaction: discord.Interaction):
    """Hinweis für die Bedienung über das Kontextmenü."""
    await interaction.response.send_message(
        "Nutze das Nachrichten-Kontextmenü und wähle „Flaggen-Übersetzung“, "
        "um die Buttons für eine konkrete Nachricht zu öffnen.",
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
    raise RuntimeError("DISCORD_TOKEN fehlt in der .env-Datei.")

bot.run(TOKEN)
import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import MyMemoryTranslator
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Flaggen → Sprachcode
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
    "🇨🇳": "zh-CN",
    "🇳🇱": "nl",
    "🇵🇱": "pl",
    "🇹🇷": "tr",
    "🇸🇦": "ar",
    "🇺🇦": "uk",
}

# ======================
# Slash Command
# ======================
@bot.tree.command(name="translate", description="Übersetzt einen Text")
@app_commands.describe(
    text="Der Text, der übersetzt werden soll",
    target="Zielsprache (z.B. de, en, fr, es, ja...)"
)
async def translate(interaction: discord.Interaction, text: str, target: str = "de"):
    await interaction.response.defer(ephemeral=True)
    
    try:
        translated = MyMemoryTranslator(source='auto', target=target.lower()).translate(text)
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Fehler: `{e}`", ephemeral=True)

# ======================
# Context Menu
# ======================
@bot.tree.context_menu(name="Übersetzen (DE)")
async def translate_to_german(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    
    if not message.content:
        await interaction.followup.send("Diese Nachricht hat keinen Text.", ephemeral=True)
        return
    
    try:
        translated = MyMemoryTranslator(source='auto', target='de').translate(message.content)
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Fehler: `{e}`", ephemeral=True)

@bot.tree.context_menu(name="Translate to English")
async def translate_to_english(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    
    if not message.content:
        await interaction.followup.send("This message has no text.", ephemeral=True)
        return
    
    try:
        translated = MyMemoryTranslator(source='auto', target='en').translate(message.content)
        await interaction.followup.send(translated, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: `{e}`", ephemeral=True)

# ======================
# Flaggen-Reaktion
# ======================
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in FLAG_LANGUAGES:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return

    if not message.content:
        return

    lang = FLAG_LANGUAGES[emoji]
    user = payload.member or await bot.fetch_user(payload.user_id)

    try:
        translated = MyMemoryTranslator(source='auto', target=lang).translate(message.content)
        
        # Private Nachricht nur an den User, der reagiert hat
        try:
            await user.send(f"**Übersetzung ({lang.upper()}):**\n{translated}")
        except discord.Forbidden:
            # Falls der User DMs deaktiviert hat, versuche ephemeral über Interaction (geht hier nicht direkt)
            pass

    except Exception as e:
        print(f"Übersetzungsfehler: {e}")

# ======================
# Ready
# ======================
@bot.event
async def on_ready():
    print(f"Bot ist online als {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Commands synchronisiert")
    except Exception as e:
        print(f"Sync-Fehler: {e}")

bot.run(TOKEN)
