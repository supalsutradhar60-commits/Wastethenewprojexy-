import os
import re
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


async def _uid(client):
    """Return the logged-in user id reliably, even if client.me is not cached yet."""
    try:
        me = client.me
        if me is None:
            me = await client.get_me()
        return int(me.id) if me else None
    except Exception as exc:
        print(f"AI Chat: unable to get client user id: {exc}")
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


# Groq on-demand has a requests-per-minute limit.  Serialize AI requests
# and keep a small gap between them so a busy group does not immediately
# burn through the RPM limit.
_groq_lock = __import__("asyncio").Lock()
_groq_next_request = 0.0
_GROQ_MIN_INTERVAL = 2.15  # safely below 30 requests/minute


async def _ask_groq(text):
    global _groq_next_request

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

    # Only one request at a time, with a minimum interval between requests.
    # This prevents multiple messages arriving together from exceeding RPM.
    async with _groq_lock:
        now = __import__("time").monotonic()
        wait_for = _groq_next_request - now
        if wait_for > 0:
            await __import__("asyncio").sleep(wait_for)

        timeout = aiohttp.ClientTimeout(total=50)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(3):
                try:
                    async with session.post(url, headers=headers, json=payload) as response:
                        data = await response.json(content_type=None)
                        _groq_next_request = __import__("time").monotonic() + _GROQ_MIN_INTERVAL

                        if response.status == 200:
                            choices = data.get("choices", [])
                            if not choices:
                                return "⚠️ AI did not return a reply."
                            return (
                                choices[0].get("message", {}).get("content", "").strip()
                                or "⚠️ AI returned an empty reply."
                            )

                        err = data.get("error", {}) if isinstance(data, dict) else {}
                        msg = err.get("message", "request failed")

                        # Groq may return a retry-after value when RPM is exceeded.
                        if response.status == 429 and attempt < 2:
                            retry_after = response.headers.get("retry-after")
                            try:
                                delay = float(retry_after)
                            except (TypeError, ValueError):
                                # The error text commonly says "Please try again in 2s".
                                match = re.search(r"try again in\s+([\d.]+)s", str(msg), re.I)
                                delay = float(match.group(1)) if match else 2.5
                            await __import__("asyncio").sleep(min(max(delay, 2.1), 10.0))
                            _groq_next_request = __import__("time").monotonic() + _GROQ_MIN_INTERVAL
                            continue

                        if response.status == 429:
                            # Don't expose the raw organization/model rate-limit dump
                            # to the Telegram chat.
                            return "⏳ AI is busy right now. Please send your message again in a few seconds."

                        return f"⚠️ Groq error: {msg}"

                except (aiohttp.ClientError, __import__("asyncio").TimeoutError) as exc:
                    if attempt < 2:
                        await __import__("asyncio").sleep(2.0)
                        continue
                    print(f"AI Chat network error: {exc}")
                    return "⚠️ AI service is temporarily unavailable. Please try again."

    return "⚠️ AI service is temporarily unavailable."


@Client.on_message(filters.command("aichat", ".") & filters.me)
async def aichat_command(client: Client, message: Message):
    uid = await _uid(client)
    args = [x.lower() for x in (message.command[1:] if message.command else [])]
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
    filters.incoming
    & filters.group
    & (filters.text | filters.caption)
    & ~filters.me
    & ~filters.bot
    & ~filters.service
)
async def aichat_reply(client: Client, message: Message):
    uid = await _uid(client)
    if not uid or not await _enabled(uid):
        return

    text = message.text or message.caption
    if not text or not text.strip():
        return

    # Never answer commands from any common Telegram command prefix.
    stripped = text.lstrip()
    if stripped.startswith((".", "/", "!")):
        return

    try:
        print(f"AI Chat: handling message in chat={message.chat.id} from={message.from_user.id if message.from_user else 'unknown'}")
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
