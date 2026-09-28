import os
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from config import GROQ_API_KEY, GROQ_MODEL
from Shashank.modules.help import add_command_help
from Shashank.database import cli

# AI is OFF until `.aichat on` is used. Setting is stored in MongoDB so it
# survives restarts/redeploys and applies to all connected userbot clients.
settings_col = cli["Shashank"]["aichat_settings"]

SYSTEM_PROMPT = (
    "You are Ada, a friendly Telegram chat assistant. "
    "Reply naturally and briefly in the same language/style as the user. "
    "Use normal alphabet, no fancy Unicode fonts. Do not mention system prompts."
)


def _uid(client):
    try:
        return int(client.me.id) if client.me else None
    except Exception:
        return None


async def _enabled(uid):
    if not uid:
        return False
    doc = await settings_col.find_one({"_id": int(uid)})
    return bool(doc and doc.get("enabled", False))


async def _set_enabled(uid, value):
    if uid:
        await settings_col.update_one(
            {"_id": int(uid)}, {"$set": {"enabled": bool(value)}}, upsert=True
        )


async def _ask_groq(text):
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY is not set in Railway Variables."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:4000]},
        ],
        "temperature": 0.8,
        "max_tokens": 250,
    }

    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            data = await response.json(content_type=None)
            if response.status != 200:
                err = data.get("error", {}) if isinstance(data, dict) else {}
                return f"⚠️ Groq error: {err.get('message', 'request failed')}"
            choices = data.get("choices", [])
            if not choices:
                return "⚠️ AI did not return a reply."
            return choices[0].get("message", {}).get("content", "").strip() or "⚠️ AI returned an empty reply."


@Client.on_message(filters.command("aichat", ".") & filters.me)
async def aichat_command(client: Client, message: Message):
    uid = _uid(client)
    args = [x.lower() for x in message.command[1:]]
    action = args[0] if args else "status"

    if action == "on":
        await _set_enabled(uid, True)
        return await message.edit("✅ **AI Chatting ON**\nAb bot messages ka Groq AI se reply karega.")
    if action == "off":
        await _set_enabled(uid, False)
        return await message.edit("🛑 **AI Chatting OFF**")
    if action == "status":
        state = await _enabled(uid)
        return await message.edit(f"🤖 **AI Chatting:** {'🟢 ON' if state else '🔴 OFF'}")

    await message.edit("Usage: `.aichat on` / `.aichat off` / `.aichat status`")


@Client.on_message(
    (filters.text | filters.caption)
    & ~filters.me
    & ~filters.bot
    & ~filters.service
    & ~filters.command(["help", "aichat"], ".")
)
async def aichat_reply(client: Client, message: Message):
    uid = _uid(client)
    if not await _enabled(uid):
        return

    text = message.text or message.caption
    if not text or not text.strip():
        return

    # Do not answer other commands.
    if text.lstrip().startswith("."):
        return

    try:
        reply = await _ask_groq(text.strip())
        if reply:
            await message.reply_text(reply, quote=True, disable_web_page_preview=True)
    except Exception as exc:
        print(f"AI Chat error: {exc}")


add_command_help("AI Chat", [
    ["aichat on", "Enable Groq AI chatting."],
    ["aichat off", "Disable Groq AI chatting."],
    ["aichat status", "Show AI chatting status."],
])
