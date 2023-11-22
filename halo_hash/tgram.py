from telegram import Bot, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackContext,
)

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot_token = "6700291814:AAHU76S800NJ2M9TKVmbY8K9TfSGf5Ys7UE"
bot = Bot(token=bot_token)


# Define a command to send a message to the group
def send_to_group(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id  # Get the ID of the group
    message_text = "Hello, this is your bot speaking!"  # Your message here
    bot.send_message(chat_id=group_id, text=message_text)


# Set up the command handler
updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler("sendtogroup", send_to_group))

# Start the bot
updater.start_polling()
updater.idle()
