import os
import discord
import requests
import re
import time
from collections import defaultdict, deque

intents = discord.Intents.default()
intents.message_content = True

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))

client = discord.Client(intents=intents)

# === Custom Instructions and Config ===

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
SCRIPT_CHANNEL = "#1400830782347677758"
SCRIPT_LINKS = {
    "sab": SCRIPT_CHANNEL,
    "steal a brainrot": SCRIPT_CHANNEL,
    "finder": SCRIPT_CHANNEL,
    "steal": SCRIPT_CHANNEL
}
ABUSE_WARNINGS = [
    "I'm not able to answer that.",
    "I'm not able to answer that. Please do not use offensive or hateful language.",
    "I'm not able to answer that. Continued attempts may result in being ignored temporarily.",
    "You have repeatedly sent offensive or hateful messages. You will be ignored for 12 hours."
]
OFFENSIVE_PATTERNS = [
    r"\bnigger\b",
    r"\bfaggot\b",
    r"\bretard\b",
    r"\bfag\b",
    r"\btranny\b",
    r"\bcoon\b",
    r"\bchink\b",
    r"\bspic\b",
    r"\bkike\b",
    r"\bdyke\b",
    r"\bslut\b",
    r"\bcunt\b",
    r"\bnazi\b",
    r"\bheil\b",
    r"\bhitler\b"
]

# How many offensive attempts before timeout (12h)
OFFENSIVE_LIMIT = 4
TIMEOUT_SECONDS = 12 * 60 * 60  # 12 hours

# Track offensive attempts and timeouts per user
user_offense_counts = defaultdict(int)
user_timeout_until = defaultdict(float)

# Simple short-term memory for each user (last 5 Q/A pairs)
user_memories = defaultdict(lambda: deque(maxlen=5))

# === Utility Functions ===

def is_key_question(q: str) -> bool:
    q = q.lower()
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
    patterns = [
        r'is.*script.*undetected',
        r'undetected.*script',
        r'is.*undetect(ed|able)',
        r'safe.*use',
        r'ban.*risk',
        r'undetected.*(for|on).*game'
    ]
    return any(re.search(p, q) for p in patterns)

def is_script_where_question(q: str) -> bool:
    q = q.lower()
    patterns = [
        r'where.*script',
        r'find.*script',
        r'get.*script',
        r'script.*where',
        r'how.*get.*script'
    ]
    return any(re.search(p, q) for p in patterns)

def is_specific_script_question(q: str) -> str:
    q = q.lower()
    # E.g. "how to get sab script", "how to get steal a brainrot script"
    for name in SCRIPT_LINKS.keys():
        if name in q and "script" in q and any(w in q for w in ["get", "find", "where", "download"]):
            return name
    return None

def which_script_link(q: str):
    q = q.lower()
    for name, channel in SCRIPT_LINKS.items():
        if name in q:
            return channel
    return None

def is_offensive(q: str) -> bool:
    q = q.lower()
    return any(re.search(p, q) for p in OFFENSIVE_PATTERNS)

def should_answer(question):
    # Only answer exploit/executor/key/script/undetected/status related questions directly
    return (
        is_key_question(question)
        or is_executor_status_question(question)
        or is_undetected_question(question)
        or is_script_where_question(question)
        or is_specific_script_question(question)
        or which_script_link(question)
    )

def get_conversation_style(question: str) -> str:
    # Infer style: Is it casual, formal, meme-y, etc.?
    # For simplicity, just detect if there's a lot of lowercase (casual) or uppercase (excited/angry), or use emojis.
    if question.isupper():
        return "shout"
    elif "😂" in question or "🤣" in question:
        return "meme"
    elif question.endswith("!") or "bro" in question or "yo" in question:
        return "casual"
    elif "pls" in question or "please" in question:
        return "polite"
    return "neutral"

def style_response(response: str, question: str) -> str:
    style = get_conversation_style(question)
    if style == "shout":
        return response.upper() + "!"
    elif style == "meme":
        return response + " 😂"
    elif style == "casual":
        return response + " bro"
    elif style == "polite":
        return "Sure! " + response
    return response

# === Discord Bot Logic ===

@client.event
async def on_ready():
    print(f"Bot is ready as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return
    if not message.content.startswith("!"):
        return

    user_id = message.author.id
    question = message.content[1:].strip()

    # Check for timeout
    now = time.time()
    if user_id in user_timeout_until and user_timeout_until[user_id] > now:
        await message.channel.send("You are temporarily ignored due to repeated offensive language. Please try again later.")
        return

    # Check for offensive message
    if is_offensive(question):
        user_offense_counts[user_id] += 1
        if user_offense_counts[user_id] >= OFFENSIVE_LIMIT:
            user_timeout_until[user_id] = now + TIMEOUT_SECONDS
            await message.channel.send(ABUSE_WARNINGS[-1])
        else:
            await message.channel.send(ABUSE_WARNINGS[user_offense_counts[user_id] - 1])
        return

    # Only answer specific topics directly
    if should_answer(question):
        # 1. Key questions
        if is_key_question(question):
            response = style_response(KEY_INSTRUCTIONS, question)
            await message.channel.send(response)
            user_memories[user_id].append(("Q", question))
            user_memories[user_id].append(("A", response))
            return

        # 2. Executor/exploit status questions
        if is_executor_status_question(question):
            response = style_response(EXECUTOR_STATUS, question)
            await message.channel.send(response)
            user_memories[user_id].append(("Q", question))
            user_memories[user_id].append(("A", response))
            return

        # 3. Undetected/safety questions
        if is_undetected_question(question):
            response = style_response(UNDETECTED_INFO, question)
            await message.channel.send(response)
            user_memories[user_id].append(("Q", question))
            user_memories[user_id].append(("A", response))
            return

        # 4. Script location questions
        specific_script = is_specific_script_question(question)
        if is_script_where_question(question) and not specific_script:
            response = style_response(SCRIPT_WHERE, question)
            await message.channel.send(response)
            user_memories[user_id].append(("Q", question))
            user_memories[user_id].append(("A", response))
            return

        # 5. Direct script requests (user answered which script)
        script_channel = None
        if specific_script:
            script_channel = SCRIPT_LINKS[specific_script]
        else:
            script_channel = which_script_link(question)
        if script_channel:
            reply = style_response(f"Check <{script_channel}> for that script.", question)
            await message.channel.send(reply)
            user_memories[user_id].append(("Q", question))
            user_memories[user_id].append(("A", reply))
            return

    # Companion: For any other question, act as a friendly, informal companion and keep the style
    # Use short-term memory to provide context if possible (last 5 Q/A)
    memory_context = "\n".join(
        [f"{qa}: {txt}" for qa, txt in user_memories[user_id]]
    )
    prompt = (
        "You're a friendly Discord companion for a Roblox exploiting server. "
        "Respond in the same style as the user and keep it short and light unless asked for detail. "
        "If the message is about keys, scripts, executors, or undetected status, always use the custom logic. "
        "Otherwise, just chat normally and stay on-topic. "
        "User may use slang, memes, or formal language; match their style. "
        f"Recent conversation:\n{memory_context}\nUser: {question}\nCompanion:"
    )

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
                    {"text": prompt}
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
        styled = style_response(gen, question)
        await message.channel.send(styled[:1900])
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", styled))
    except Exception as e:
        await message.channel.send(f"Error: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN environment variable not set.")
    elif not ALLOWED_CHANNEL_ID:
        print("ALLOWED_CHANNEL_ID environment variable not set or is 0.")
    else:
        client.run(DISCORD_TOKEN)
