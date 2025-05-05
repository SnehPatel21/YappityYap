import discord
from discord import app_commands, Forbidden
from discord.ext import commands
import os
import requests
import asyncio
import io
import re
from dotenv import load_dotenv

# Load environment variables
dotenv_loaded = load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
LM_API_URL = os.getenv("LM_API_URL")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))  # Your test guild ID
TEST_GUILD = discord.Object(id=GUILD_ID)

# Setup bot intents and client
intents = discord.Intents.default()
intents.message_content = False  # Not needed for slash commands
bot = commands.Bot(command_prefix="!", intents=intents)

async def query_local_llm(prompt: str, max_tokens: int = 100000) -> str:
    """
    Query the local LLM via chat-completions endpoint, using only 'user' role to satisfy local LLM templates.
    """
    payload = {
        "model": os.getenv("LM_MODEL", "local-model"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(LM_API_URL, json=payload))
        data = response.json()
        if not isinstance(data, dict) or "choices" not in data:
            print(f"Unexpected LLM response: {data}")
            return "⚠️ Received unexpected response from the LLM."
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "⚠️ Unable to contact the LLM server at this time. Please try again later."

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=TEST_GUILD)
        print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
    except Forbidden:
        synced = await bot.tree.sync()
        print(f"⚠️ Missing access to guild {GUILD_ID}, globally synced {len(synced)} commands instead.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# Helper to send or split long content
async def send_long_content(interaction, content: str):
    # If code blocks present, extract and send as .py file
    code_blocks = re.findall(r"```(?:\w*\n)?(.*?)```", content, re.DOTALL)
    if code_blocks:
        code_content = "\n\n".join(code_blocks)
        file = discord.File(fp=io.StringIO(code_content), filename="response.txt")
        await interaction.followup.send(content="📦 The response includes code. Here's the file:", file=file)
        return

    # Else split into chunks ≤ 2000 chars
    if len(content) <= 2000:
        await interaction.followup.send(content)
    else:
        await interaction.followup.send("📖 The response is long; splitting into parts:")
        for i in range(0, len(content), 2000):
            await interaction.followup.send(content[i:i+2000])

# Slash command: /ask
@bot.tree.command(name="ask", description="Ask the AI anything.")
@app_commands.describe(
    question="Your question to the AI.",
    max_tokens="Max response length in tokens (default 512)"
)
async def slash_ask(
    interaction: discord.Interaction,
    question: str,
    max_tokens: int = 100000
):
    await interaction.response.defer(thinking=True)
    answer = await query_local_llm(question, max_tokens)
    await send_long_content(interaction, f"🧠 {answer}")

# Slash command: /joke
@bot.tree.command(name="joke", description="Get a funny AI-generated joke.")
async def slash_joke(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    answer = await query_local_llm("Tell me a short funny joke.", 200)
    await send_long_content(interaction, f"😂 {answer}")

# Slash command: /wyr
@bot.tree.command(name="wyr", description="Would You Rather question.")
async def slash_wyr(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    answer = await query_local_llm("Give me a 'Would You Rather' question.", 200)
    await send_long_content(interaction, f"🤔 {answer}")

# Slash command: /summarize
@bot.tree.command(name="summarize", description="Summarize the last 10 messages in this channel.")
async def slash_summarize(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    msgs = [msg async for msg in interaction.channel.history(limit=15) if not msg.author.bot]
    chat_log = "\n".join(f"{m.author.display_name}: {m.content}" for m in reversed(msgs[-10:]))
    summary = await query_local_llm(f"Summarize this conversation:\n{chat_log}", 300)
    await send_long_content(interaction, f"📋 {summary}")

# Slash command: /health
@bot.tree.command(name="health", description="Check bot and LLM server health.")
async def slash_health(interaction: discord.Interaction):
    try:
        res = requests.get(os.getenv("LM_API_URL_PING"), timeout=2)
        status = "🟢 LLM is up" if res.status_code == 200 else f"⚠️ LLM status: {res.status_code}"
    except Exception:
        status = "🔴 Cannot reach LLM server."
    await interaction.response.send_message(f"🏓 Bot is online. {status}")

if __name__ == "__main__":
    bot.run(TOKEN)