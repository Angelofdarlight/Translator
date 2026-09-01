import discord
from discord import app_commands
from discord.ext import commands
from deep_translator import GoogleTranslator
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
        translated = GoogleTranslator(source='auto', target=target.lower()).translate(text)
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
        translated = GoogleTranslator(source='auto', target='de').translate(message.content)
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
        translated = GoogleTranslator(source='auto', target='en').translate(message.content)
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
        translated = GoogleTranslator(source='auto', target=lang).translate(message.content)
        
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
