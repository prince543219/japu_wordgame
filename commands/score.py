from telethon import events

async def command_handler(event):
    # Get user information and send a welcome message
    user = await event.get_sender()
    await event.reply(f"Hello, {user.first_name}! Welcome to the Word Game Bot! 🎮")

