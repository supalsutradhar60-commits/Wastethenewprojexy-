from pyrogram import filters, Client
from pyrogram.types import Message
import Shashank.database.pmpermitdb as Shashank
from Shashank.database.pmpermitdb import get_approved_users, pm_guard
from config import LOG_GROUP, PM_LOGGER

USERS_AND_WARNS = {}


async def denied_users(filter, client: Client, message: Message):
    if not await pm_guard():
        return False
    if message.chat.id in (await get_approved_users()):
        return False
    return True


def get_arg(message):
    msg = message.text or ""
    if len(msg) > 1 and msg[1] == " ":
        msg = msg.replace(" ", "", 1)
    split = msg[1:].replace("\n", " \n").split(" ")
    if " ".join(split[1:]).strip() == "":
        return ""
    return " ".join(split[1:])


@Client.on_message(filters.command("setlimit", ["."]) & filters.me)
async def pmguard(client, message):
    arg = get_arg(message)
    if not arg:
        return await message.edit("**Set limit to what?**")
    await Shashank.set_limit(int(arg))
    await message.edit(f"**Limit set to {arg}**")


@Client.on_message(filters.command("setblockmsg", ["."]) & filters.me)
async def setpmmsg(client, message):
    arg = get_arg(message)
    if not arg:
        return await message.edit("**What message to set**")
    if arg == "default":
        await Shashank.set_block_message(Shashank.BLOCKED)
        return await message.edit("**Block message set to default**.")
    await Shashank.set_block_message(f"`{arg}`")
    await message.edit("**Custom block message set**")


@Client.on_message(filters.command(["allow", "ap", "approve", "a"], ["."]) & filters.me & filters.private)
async def allow(client, message):
    chat_id = message.chat.id
    await Shashank.allow_user(chat_id)
    await Shashank.mark_promo_sent(chat_id)
    await message.edit(f"**I have allowed [you](tg://user?id={chat_id}) to PM me.**")


@Client.on_message(filters.command(["deny", "dap", "disapprove", "dapp"], ["."]) & filters.me & filters.private)
async def deny(client, message):
    chat_id = message.chat.id
    await Shashank.deny_user(chat_id)
    await message.edit(f"**I have denied [you](tg://user?id={chat_id}) to PM me.**")


@Client.on_message(
    filters.private
    & filters.create(denied_users)
    & filters.incoming
    & ~filters.service
    & ~filters.me
    & ~filters.bot
)
async def reply_pm(app: Client, message: Message):
    """Send the PM promotion only once per user/new DM chat.

    The sent flag is stored in MongoDB, so restarts/redeploys do not make the
    same person receive the promotion again.
    """
    try:
        if await Shashank.promo_was_sent(message.chat.id):
            return

        _, pm_message, _, _ = await Shashank.get_pm_settings()
        if PM_LOGGER:
            try:
                await app.send_message(PM_LOGGER, message.text or "[media]")
            except Exception:
                pass

        await message.reply_text(pm_message, disable_web_page_preview=True)
        await Shashank.mark_promo_sent(message.chat.id)
    except Exception as exc:
        print(f"PM promo error: {exc}")
