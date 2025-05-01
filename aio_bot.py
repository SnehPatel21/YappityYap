import discord
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
LM_API_URL = os.getenv("LM_API_URL")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def query_local_llm(prompt):
    payload = {
        "prompt": prompt,
        "max_tokens": 200,
        "temperature": 0.7,
        "stop": None
    }
    try:
        res = requests.post(LM_API_URL, json=payload)
        return res.json()["choices"][0]["text"].strip()
    except Exception as e:
        return f"Error contacting LLM: {e}"

@client.event
async def on_ready():
    print(f"✅ AIO is live as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    # Ask AI anything
    if content.startswith("!ask "):
        prompt = content[5:]
        await message.channel.send("🤔 Thinking...")
        response = await query_local_llm(prompt)
        await message.channel.send(f"🧠 {response}")

    # Generate a joke
    elif content.startswith("!joke"):
        prompt = "Tell me a short funny joke"
        response = await query_local_llm(prompt)
        await message.channel.send(f"😂 {response}")

    # Would You Rather
    elif content.startswith("!wyr"):
        prompt = "Give me a 'Would You Rather' question"
        response = await query_local_llm(prompt)
        await message.channel.send(f"🤔 {response}")

    # Summarize last 10 messages
    elif content.startswith("!summarize"):
        messages = [msg async for msg in message.channel.history(limit=10) if not msg.author.bot]
        chat_text = "\n".join([f"{m.author.name}: {m.content}" for m in reversed(messages)])
        prompt = f"Summarize this conversation:\n{chat_text}"
        response = await query_local_llm(prompt)
        await message.channel.send(f"📋 {response}")

client.run(TOKEN)