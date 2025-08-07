import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))  # Set your channel ID in env

def is_allowed_channel(ctx):
    return ctx.channel.id == ALLOWED_CHANNEL_ID

@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}")

@bot.command()
@commands.check(is_allowed_channel)
async def hello(ctx):
    await ctx.send("Hello there!")

@bot.command()
@commands.check(is_allowed_channel)
async def ask(ctx, *, question):
    """Ask Gemini AI a question."""
    if not GEMINI_API_KEY:
        await ctx.send("Gemini API key not set.")
        return

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": question}]}]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        response = requests.post(url, headers=headers, params=params, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()
        gen = result["candidates"][0]["content"]["parts"][0]["text"]
        await ctx.send(gen[:1900])
    except Exception as e:
        await ctx.send(f"Error: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(DISCORD_TOKEN)
