# © By Shashank shukla (Github = itzshukla) You are motherfucker if you Don't gives credits.

from pyrogram import filters, Client
import asyncio
from pyrogram.types import Message 
from pyrogram.methods import messages
from Shashank.database.pmpermitdb import get_approved_users, pm_guard, has_received_first_dm, mark_first_dm
import Shashank.database.pmpermitdb as Shashank
from config import LOG_GROUP, PM_LOGGER
FLOOD_CTRL = 0
ALLOWED = []
USERS_AND_WARNS = {}

async def denied_users(filter, client: Client, message: Message):
    if not await pm_guard():
        return False
    if message.chat.id in (await get_approved_users()):
        return False
    else:
        return True

def get_arg(message):
    msg = message.text
    msg = msg.replace(" ", "", 1) if msg[1] == " " else msg
    split = msg[1:].replace("\n", " \n").split(" ")
    if " ".join(split[1:]).strip() == "":
        return ""
    return " ".join(split[1:])


@Client.on_message(filters.command("setlimit", ["."]) & filters.me)
async def pmguard(client, message):
    arg = get_arg(message)
    if not arg:
        await message.edit("**Set limit to what?**")
        return
    await Shashank.set_limit(int(arg))
    await message.edit(f"**Limit set to {arg}**")



@Client.on_message(filters.command("setblockmsg", ["."]) & filters.me)
async def setpmmsg(client, message):
    arg = get_arg(message)
    if not arg:
        await message.edit("**What message to set**")
        return
    if arg == "default":
        await Shashank.set_block_message(Shashank.BLOCKED)
        await message.edit("**Block message set to default**.")
        return
    await Shashank.set_block_message(f"`{arg}`")
    await message.edit("**Custom block message set**")


@Client.on_message(filters.command(["allow", "ap", "approve", "a"], ["."]) & filters.me & filters.private)
async def allow(client, message):
    chat_id = message.chat.id
    pmpermit, pm_message, limit, block_message = await Shashank.get_pm_settings()
    await Shashank.allow_user(chat_id)
    await message.edit(f"**I have allowed [you](tg://user?id={chat_id}) to PM me.**")
    async for message in client.search_messages(
        chat_id=message.chat.id, query=pm_message, limit=1, from_user="me"
    ):
        await message.delete()
    USERS_AND_WARNS.update({chat_id: 0})


@Client.on_message(filters.command(["deny", "dap", "disapprove", "dapp"], ["."]) & filters.me & filters.private)
async def deny(client, message):
    chat_id = message.chat.id
    await Shashank.deny_user(chat_id)
    await message.edit(f"**I have denied [you](tg://user?id={chat_id}) to PM me.**")


@Client.on_message(
    filters.private
    & filters.incoming
    & ~filters.service
    & ~filters.me
    & ~filters.bot
)
async def reply_pm(app: Client, message: Message):
    """Send the automatic DM message only once per user.

    After the first message, the AI chat module can handle the conversation.
    The old repeated-warning/block loop is intentionally not used here.
    """
    if await has_received_first_dm(message.chat.id):
        return

    pmpermit, pm_message, limit, block_message = await Shashank.get_pm_settings()
    if PM_LOGGER:
        try:
            await app.send_message(PM_LOGGER, f"{message.text or ''}")
        except Exception:
            pass

    try:
        await message.reply(pm_message, disable_web_page_preview=True)
        await mark_first_dm(message.chat.id)
    except Exception as e:
        print(f"First DM message error: {e}")

