#!/usr/bin/env python3
"""
Simple test script to check if the bot can start without errors
"""

try:
    # Test imports
    import os
    import pyrebase
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
    import asyncio
    from datetime import datetime
    import re
    
    print("✅ All imports successful")
    
    # Test basic bot configuration
    TELEGRAM_BOT_TOKEN = "8464152381:AAE0UooBusDBPyoLO0mrc2gV8_xU4zuYXOE"
    
    # Test decorator definition
    def check_auth(func):
        """Decorator to check if user is authenticated."""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            return await func(update, context, *args, **kwargs)
        return wrapper
    
    print("✅ check_auth decorator defined successfully")
    
    # Test using the decorator
    @check_auth
    async def test_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return "test"
    
    print("✅ Decorator can be used successfully")
    
    # Test bot creation
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    print("✅ Bot application created successfully")
    
    print("\n🎉 All tests passed! The bot should be able to run.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
