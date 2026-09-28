from pyrogram import Client, filters, enums
from pyrogram.types import Message
from Shashank import app, CMD_HELP, SUDO_USER

HELP_MENU = r"""<blockquote>| ❁ ＷＡＳＴＥ Ｘ ＵＢＯＴ - ＨＥＬＰ ＭＥＮＵ ❁ |
+-----------------------+------------------------+
| Autopic               | admin                  |
| afk                   | animation              |
| anime_cf              | antipm                 |
| autoscroll            | banall                 |
| birthday              | broadcast              |
| carbon                | clone                  |
| create                | destruct               |
| dictionary            | dmspam                 |
| emoji                 | flirt                  |
| globals               | google                 |
| info                  | invite                 |
| joinleave             | locks                  |
| memify                | mention                |
| metrics               | paste                  |
| pats                  | ping                   |
| profile               | purge                  |
| quotly                | raid                   |
| replyraid             | restart                |
| sangmata              | screenshot             |
| spam                  | start                  |
| stats                 | sticker                |
| stickers              | sudos                  |
| tag                   | tagalert               |
| tagall                | text                   |
| tiny                  | translate              |
| truth-dare            | update                 |
| upload                | vctools                |
| vulgar                | waifu                  |
| weather               | VcFight                |
| promotion             | aichat                 |
+-----------------------+------------------------+
• @II_JPEXO_II × @JP_NETWORK .</blockquote>"""


def _find_help_key(name: str):
    name = (name or "").strip().lower()
    for key in CMD_HELP:
        if key.lower() == name:
            return key
    return None


@Client.on_message(
    filters.command(["help", "helpme"], ".") & (filters.me | filters.user(SUDO_USER))
)
async def module_help(client: Client, message: Message):
    cmd = message.command
    help_arg = " ".join(cmd[1:]).strip() if len(cmd) > 1 else ""

    if not help_arg:
        return await message.reply_text(
            HELP_MENU, parse_mode=enums.ParseMode.HTML
        )

    key = _find_help_key(help_arg)
    if key:
        commands = CMD_HELP[key]
        this_command = f"──「 **Help For {str(key).upper()}** 」──\n\n"
        for x in commands:
            this_command += (
                f"  • **Command:** `.{str(x)}`\n"
                f"  • **Function:** `{str(commands[x])}`\n\n"
            )
        return await message.reply_text(
            this_command, parse_mode=enums.ParseMode.MARKDOWN
        )

    await message.reply_text(f"`{help_arg}` **Not a Valid Module Name.**")


async def module_helper(client: Client, message: Message):
    help_arg = ""

    if message.reply_to_message and message.reply_to_message.text:
        help_arg = message.reply_to_message.text.strip()
    elif len(message.command) > 1:
        help_arg = " ".join(message.command[1:]).strip()

    if not help_arg:
        return await message.reply_text(
            HELP_MENU, parse_mode=enums.ParseMode.HTML
        )

    key = _find_help_key(help_arg)
    if key:
        commands = CMD_HELP[key]
        this_command = f"──「 **Help For {str(key).upper()}** 」──\n\n"
        for x in commands:
            this_command += (
                f"  • **Command:** `.{str(x)}`\n"
                f"  • **Function:** `{str(commands[x])}`\n\n"
            )
        return await message.reply_text(
            this_command, parse_mode=enums.ParseMode.MARKDOWN
        )

    await message.reply_text(f"`{help_arg}` **Not a Valid Module Name.**")


def add_command_help(module_name, commands):
    command_dict = CMD_HELP.get(module_name, {})
    for item in commands:
        if not item:
            continue
        command_dict[item[0]] = item[1]
    CMD_HELP[module_name] = command_dict
