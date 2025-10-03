python bot.py

import os
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 6968357995  # Apna Telegram ID yaha daal
DB_FILE = "books.db"

# ===== DATABASE SETUP =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            file_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Temporary storage for owner category selection
current_category = {}

# ===== COMMANDS =====

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Type a category name to get books.\n"
        "Owner can use /setcategory <name> and send books."
    )

# Owner-only: /setcategory
async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not allowed to use this command.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("❌ Please give a category name.\nExample: /setcategory PhysicsWallah")
        return

    category = " ".join(context.args).lower()
    current_category[OWNER_ID] = category
    await update.message.reply_text(f"✅ Category set to: {category.title()}\nNow send books to save.")

# Owner-only: add book (document)
async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return  # ignore non-owner

    category = current_category.get(OWNER_ID)
    if not category:
        await update.message.reply_text("❌ Set a category first using /setcategory")
        return

    doc = update.message.document
    if doc:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO books (category, title, file_id) VALUES (?, ?, ?)",
                  (category, doc.file_name, doc.file_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"📚 Saved `{doc.file_name}` under {category.title()}.", parse_mode="Markdown")

# User search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, file_id FROM books WHERE category=?", (query,))
    results = c.fetchall()
    conn.close()

    if results:
        sent_msgs = []

        # Send all books
        for title, file_id in results:
            msg = await update.message.reply_document(file_id, caption=title)
            sent_msgs.append(msg.message_id)

        # Warning message
        warn_msg = await update.message.reply_text(
            "⚠️ 3 minut Baad books remove ho jaega copyright issues ki wjh se, saved kr lo"
        )
        sent_msgs.append(warn_msg.message_id)

        # Delete messages after 3 minutes
        await asyncio.sleep(180)
        for msg_id in sent_msgs:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            except:
                pass  # ignore if already deleted
    else:
        await update.message.reply_text("❌ No books found for this category.")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Owner commands
    app.add_handler(CommandHandler("setcategory", set_category))
    app.add_handler(MessageHandler(filters.Document.ALL, add_book))

    # User search
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    # Start command
    app.add_handler(CommandHandler("start", start))

    app.run_polling()

if __name__ == "__main__":
    main()
