import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import DeeplTranslator
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
# Für sofortige Command-Synchronisierung optional die Discord-Server-ID setzen.
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translate_bot")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# DeepL unterstützt nicht jede Google-Translate-Sprache. Diese Liste enthält
# die von DeepL unterstützten Zielsprachen und mehrere passende Flaggen.
FLAG_LANGUAGES = {
    # DeeplTranslator erwartet diese Codes in Kleinbuchstaben.
    "🇩🇪": "de", "🇦🇹": "de", "🇨🇭": "de",
    "🇬🇧": "en", "🇺🇸": "en", "🇨🇦": "en", "🇦🇺": "en",
    "🇫🇷": "fr",
    "🇪🇸": "es", "🇲🇽": "es", "🇦🇷": "es",
    "🇮🇹": "it",
    "🇵🇹": "pt", "🇧🇷": "pt",
    "🇳🇱": "nl",
    "🇵🇱": "pl", "🇷🇺": "ru", "🇺🇦": "uk",
    "🇨🇿": "cs", "🇸🇰": "sk", "🇸🇮": "sl",
    "🇭🇺": "hu", "🇷🇴": "ro", "🇧🇬": "bg",
    "🇩🇰": "da", "🇸🇪": "sv", "🇳🇴": "nb", "🇫🇮": "fi",
    "🇬🇷": "el", "🇹🇷": "tr", "🇮🇩": "id",
    "🇯🇵": "ja", "🇨🇳": "zh", "🇰🇷": "ko",
}

LANGUAGE_NAMES = {
    "de": "Deutsch", "en": "Englisch", "fr": "Französisch",
    "es": "Spanisch", "it": "Italienisch", "pt": "Portugiesisch",
    "nl": "Niederländisch", "pl": "Polnisch", "ru": "Russisch",
    "uk": "Ukrainisch", "cs": "Tschechisch", "sk": "Slowakisch",
    "sl": "Slowenisch", "hu": "Ungarisch", "ro": "Rumänisch",
    "bg": "Bulgarisch", "da": "Dänisch", "sv": "Schwedisch",
    "nb": "Norwegisch", "fi": "Finnisch", "el": "Griechisch",
    "tr": "Türkisch", "id": "Indonesisch", "ja": "Japanisch",
    "zh": "Chinesisch", "ko": "Koreanisch",
}

LANGUAGE_PAGE_SIZE = 20


def split_message(text: str, limit: int = 2_000) -> list[str]:
    parts: list[str] = []
    remaining = text or "(Keine Übersetzung verfügbar.)"
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


async def translate_text(text: str, target: str) -> str:
    """DeepL ist synchron; die Anfrage läuft deshalb in einem Worker-Thread."""
    if not DEEPL_API_KEY:
        raise RuntimeError("DEEPL_API_KEY ist in Railway nicht gesetzt.")

    return await asyncio.to_thread(
        lambda: DeeplTranslator(
            api_key=DEEPL_API_KEY,
            source="auto",
            target=target,
        ).translate(text)
    )


class TranslationButton(discord.ui.Button):
    def __init__(self, emoji: str, target_language: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=LANGUAGE_NAMES.get(target_language, target_language),
            custom_id=f"translate:{emoji}",
        )
        self.target_language = target_language

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, TranslationView):
            await interaction.response.send_message("Diese Schaltfläche ist abgelaufen.", ephemeral=True)
            return

        source_message = view.source_message
        if not source_message.content:
            await interaction.response.send_message("Diese Nachricht hat keinen Text.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            translated = await translate_text(source_message.content, self.target_language)
            language = LANGUAGE_NAMES.get(self.target_language, self.target_language)
            await interaction.followup.send(
                f"**Übersetzung: {language}**\nQuelle: {source_message.jump_url}",
                ephemeral=True,
            )
            for part in split_message(translated):
                await interaction.followup.send(part, ephemeral=True)
        except Exception as error:
            logger.exception("DeepL-Übersetzung fehlgeschlagen")
            await interaction.followup.send(
                f"Übersetzung fehlgeschlagen: `{error}`", ephemeral=True
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
        if not isinstance(view, TranslationView):
            await interaction.response.send_message("Diese Ansicht ist abgelaufen.", ephemeral=True)
            return
        new_page = max(0, min(view.page + self.direction, view.page_count - 1))
        new_view = TranslationView(view.source_message, new_page)
        await interaction.response.edit_message(
            content=new_view.page_text(), view=new_view
        )


class TranslationView(discord.ui.View):
    def __init__(self, source_message: discord.Message, page: int = 0):
        super().__init__(timeout=900)
        self.source_message = source_message
        self.page = page
        self.language_items = list(FLAG_LANGUAGES.items())
        self.page_count = max(
            1, (len(self.language_items) + LANGUAGE_PAGE_SIZE - 1) // LANGUAGE_PAGE_SIZE
        )

        start = page * LANGUAGE_PAGE_SIZE
        for emoji, target_language in self.language_items[start:start + LANGUAGE_PAGE_SIZE]:
            self.add_item(TranslationButton(emoji, target_language))
        if page > 0:
            self.add_item(PageButton(-1))
        if page < self.page_count - 1:
            self.add_item(PageButton(1))

    def page_text(self) -> str:
        return (
            f"Wähle eine Flagge für die gewünschte Sprache. "
            f"Seite {self.page + 1}/{self.page_count}. "
            "Das Ergebnis wird nur dir angezeigt."
        )


@bot.tree.context_menu(name="Flaggen-Übersetzung")
async def add_translation_buttons(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        await interaction.response.send_message("Diese Nachricht hat keinen Text.", ephemeral=True)
        return
    view = TranslationView(message)
    await interaction.response.send_message(content=view.page_text(), view=view, ephemeral=True)


@bot.tree.command(name="translate", description="Übersetzt einen Text mit DeepL")
@app_commands.describe(text="Der Text", target="DeepL-Zielcode, z. B. DE, EN-US oder FR")
async def translate(interaction: discord.Interaction, text: str, target: str = "DE"):
    target = target.lower()
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.followup.send(await translate_text(text, target), ephemeral=True)
    except Exception as error:
        await interaction.followup.send(f"Übersetzung fehlgeschlagen: `{error}`", ephemeral=True)


@bot.tree.command(name="translate_buttons", description="Zeigt private Flaggen-Buttons für eine Nachricht an")
async def translate_buttons(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Öffne das Nachrichten-Kontextmenü und wähle „Flaggen-Übersetzung“.",
        ephemeral=True,
    )


@bot.event
async def on_ready():
    logger.info("Bot ist online als %s", bot.user)
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info("%s Server-Commands synchronisiert", len(synced))
        else:
            synced = await bot.tree.sync()
            logger.info("%s globale Commands synchronisiert", len(synced))
    except Exception:
        logger.exception("Command-Synchronisierung fehlgeschlagen")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN fehlt.")
if not DEEPL_API_KEY:
    raise RuntimeError("DEEPL_API_KEY fehlt.")

bot.run(TOKEN)
