import os
import discord
import requests
import re

intents = discord.Intents.default()
intents.message_content = True

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))

client = discord.Client(intents=intents)

KEY_INSTRUCTIONS = (
    "The key is on the website https://w1ckllon.com/ .\n"
    "To generate a key, you have to create an account (it doesn't have to be your Roblox account; it could be anything else).\n"
    "Then click the 'Generate Key' button — it's at the top middle of the screen on mobile and the top right on PC."
)
EXECUTOR_STATUS = (
    "To check which executors are working right now, visit https://whatexpsare.online/ for up-to-date status."
)
UNDETECTED_INFO = (
    "Yes, the script is undetected for all the games that are supported."
)
SCRIPT_WHERE = (
    "Which script are you looking for?"
)
SCRIPT_LINKS = {
    "sab": "#1400830782347677758",
    "steal a brainrot": "#1400830782347677758",
    "finder": "#1400830782347677758",
    "steal": "#1400830782347677758"
}
# Add more script aliases as needed

def is_key_question(q: str) -> bool:
    q = q.lower()
    # match various ways to ask about the key
    patterns = [
        r'\bhow (do i|to) (get|generate|find|obtain|make).*\bkey\b',
        r'\bwhere (is|can i get|to get|do i get).*\bkey\b',
        r'\bkey\b.*(where|how|get|generate|find|obtain|make)',
        r'\bget.*key\b',
        r'\bkey.*get\b'
    ]
    return any(re.search(p, q) for p in patterns) or ('key' in q and any(w in q for w in ['where', 'how', 'get', 'generate', 'find', 'obtain', 'make']))

def is_executor_status_question(q: str) -> bool:
    q = q.lower()
    # common phrasings for executor status
    patterns = [
        r'(which|what).*(executor|exploit).*work(ing)?',
        r'(which|what).*(executor|exploit).*up',
        r'(executor|exploit).*status',
        r'is.*(executor|exploit).*working',
        r'what.*executor.*right now',
        r'which.*executor.*online'
    ]
    return any(re.search(p, q) for p in patterns) or ('executor' in q and any(w in q for w in ['work', 'up', 'status', 'online', 'what', 'which']))

def is_undetected_question(q: str) -> bool:
    q = q.lower()
    # questions about undetected status
    patterns = [
        r'is.*script.*undetected',
        r'undetected.*script',
        r'is.*undetect(ed|able)',
        r'safe.*use',
        r'ban.*risk',
    ]
    return any(re.search(p, q) for p in patterns)

def is_script_where_question(q: str) -> bool:
    q = q.lower()
    # where to find script
    patterns = [
        r'where.*script',
        r'find.*script',
        r'get.*script',
        r'script.*where',
    ]
    return any(re.search(p, q) for p in patterns)

def which_script_link(q: str):
    q = q.lower()
    for name, channel in SCRIPT_LINKS.items():
        if name in q:
            return channel
    return None

@client.event
async def on_ready():
    print(f"Bot is ready as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return
    if message.content.startswith("!"):
        question = message.content[1:].strip()
        if not question:
            await message.channel.send("Please enter a question after the !")
            return

        # Handle key questions
        if is_key_question(question):
            await message.channel.send(KEY_INSTRUCTIONS)
            return

        # Handle executor status questions
        if is_executor_status_question(question):
            await message.channel.send(EXECUTOR_STATUS)
            return

        # Handle undetected/script safety questions
        if is_undetected_question(question):
            await message.channel.send(UNDETECTED_INFO)
            return

        # Handle 'where script' questions
        if is_script_where_question(question):
            await message.channel.send(SCRIPT_WHERE)
            return

        # If user answered with a script name, reply with the channel
        script_channel = which_script_link(question)
        if script_channel:
            await message.channel.send(f"Check <{script_channel}> for that script.")
            return

        if not GEMINI_API_KEY:
            await message.channel.send("Gemini API key not set.")
            return

        url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": question}
                    ]
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, params=params, json=data, timeout=20)
            response.raise_for_status()
            result = response.json()
            gen = (
                result.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "Sorry, I couldn't get a response from Gemini.")
            )
            await message.channel.send(gen[:1900])
        except Exception as e:
            await message.channel.send(f"Error: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN environment variable not set.")
    elif not ALLOWED_CHANNEL_ID:
        print("ALLOWED_CHANNEL_ID environment variable not set or is 0.")
    else:
        client.run(DISCORD_TOKEN)
