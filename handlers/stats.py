import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    stats = db.get_user_stats(user_id)
    if not stats:
        await update.message.reply_text("Sizda hozircha hech qanday natija yo'q.")
        return
        
    text = "Sizning natijalaringiz:\n\n"
    for row in stats:
        # row = (topic, correct_count_sum, total_count_sum)
        topic, correct, total = row
        text += f"Mavzu: {topic}\nTo'g'ri javoblar: {correct}/{total}\n\n"
        
    await update.message.reply_text(text)

async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if context.args and context.args[0].lower() == "umumiy":
        # Umumiy reyting
        res = db.get_chat_rating(chat_id)
        if not res:
            await update.message.reply_text("Bu guruhda hozircha natijalar yo'q.")
            return
            
        text = "Umumiy TOP-10 Reyting:\n\n"
        for idx, row in enumerate(res):
            text += f"{idx+1}. {row[0] or 'NoName'} - {row[1]}/{row[2]}\n"
        await update.message.reply_text(text)
        return
        
    # Aks holda mavzuni tanlashni so'raymiz
    topics = db.get_topics()
    if not topics:
        await update.message.reply_text("Hozircha natijalar yo'q.")
        return
        
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(topic, callback_data=f"rating_{topic}")])
        
    keyboard.append([InlineKeyboardButton("Umumiy", callback_data="rating_umumiy")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qaysi mavzu bo'yicha reytingni ko'rmoqchisiz?", reply_markup=reply_markup)

async def rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    if data.startswith("rating_"):
        topic = data.replace("rating_", "", 1)
        
        if topic == "umumiy":
            res = db.get_chat_rating(chat_id)
            title = "Umumiy"
        else:
            res = db.get_chat_rating(chat_id, topic)
            title = f"'{topic}' mavzusi bo'yicha"
            
        if not res:
            text = f"{title} TOP-10 Reyting:\n\nHozircha natijalar yo'q."
        else:
            text = f"{title} TOP-10 Reyting:\n\n"
            for idx, row in enumerate(res):
                text += f"{idx+1}. {row[0] or 'NoName'} - {row[1]}/{row[2]}\n"
                
        await query.edit_message_text(text)
