import os
import discord
import requests

intents = discord.Intents.default()
intents.message_content = True

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))  # Set your channel ID in env

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot is ready as {client.user}")

@client.event
async def on_message(message):
    # Ignore messages from bots (including itself)
    if message.author.bot:
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    # Check if message starts with !
    if message.content.startswith("!"):
        question = message.content[1:].strip()
        if not question:
            await message.channel.send("Please enter a question after the !")
            return

        if not GEMINI_API_KEY:
            await message.channel.send("Gemini API key not set.")
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
            await message.channel.send(gen[:1900])
        except Exception as e:
            await message.channel.send(f"Error: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN environment variable not set.")
    else:
        client.run(DISCORD_TOKEN)
