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
    # Only answer exploit/executor/key/script/undetected/status related questions
    return (
        is_key_question(question)
        or is_executor_status_question(question)
        or is_undetected_question(question)
        or is_script_where_question(question)
        or is_specific_script_question(question)
        or which_script_link(question)
    )

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

    # Only answer specific topics
    if not should_answer(question):
        await message.channel.send("I'm only able to answer questions related to keys, scripts (sab, steal a brainrot, finder, steal), executors, and script undetected status. Please ask something specific to those topics.")
        return

    # === Handle all logic for whitelisted questions below ===
    # 1. Key questions
    if is_key_question(question):
        await message.channel.send(KEY_INSTRUCTIONS)
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", KEY_INSTRUCTIONS))
        return

    # 2. Executor/exploit status questions
    if is_executor_status_question(question):
        await message.channel.send(EXECUTOR_STATUS)
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", EXECUTOR_STATUS))
        return

    # 3. Undetected/safety questions
    if is_undetected_question(question):
        await message.channel.send(UNDETECTED_INFO)
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", UNDETECTED_INFO))
        return

    # 4. Script location questions
    specific_script = is_specific_script_question(question)
    if is_script_where_question(question) and not specific_script:
        await message.channel.send(SCRIPT_WHERE)
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", SCRIPT_WHERE))
        return

    # 5. Direct script requests (user answered which script)
    script_channel = None
    if specific_script:
        script_channel = SCRIPT_LINKS[specific_script]
    else:
        script_channel = which_script_link(question)
    if script_channel:
        reply = f"Check <{script_channel}> for that script."
        await message.channel.send(reply)
        user_memories[user_id].append(("Q", question))
        user_memories[user_id].append(("A", reply))
        return

    # 6. Fallback: Should never reach here, but if so, block
    await message.channel.send("I can only answer questions about keys, the allowed scripts, executors, and undetected status.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN environment variable not set.")
    elif not ALLOWED_CHANNEL_ID:
        print("ALLOWED_CHANNEL_ID environment variable not set or is 0.")
    else:
        client.run(DISCORD_TOKEN)
