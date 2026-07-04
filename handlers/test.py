import logging
import asyncio
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

async def start_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat adminlar sinovni boshlashi mumkin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Sizda bu buyruqni ishlatish uchun ruxsat yo'q. Faqatgina adminlar testni boshlay oladi.")
        return

    # Agar guruhda bo'lmasa, ogohlantirish (xohlasangiz olib tashlash mumkin)
    if update.effective_chat.type == "private":
        await update.message.reply_text("Ushbu buyruqni guruhlarda ishlatganingiz ma'qul, lekin bu yerda ham ishlatsa bo'ladi.")
    
    # Agar /test <mavzu> yozilgan bo'lsa
    if context.args:
        topic = " ".join(context.args)
        await start_test_for_topic(update.effective_chat.id, topic, context)
        return
        
    topics = db.get_topics()
    if not topics:
        await update.message.reply_text("Hozircha birorta ham mavzu va savol yo'q.")
        return
        
    # Mavzularni tugma qilib chiqaramiz
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(topic, callback_data=f"topic_{topic}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qaysi mavzuda test o'tkazmoqchisiz?", reply_markup=reply_markup)

async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Faqat admin bosa oladimi yoki ixtiyoriy kishimi? Faqat admin test boshlay olishini ta'minlash uchun:
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("Sizda test boshlash uchun ruxsat yo'q.", show_alert=True)
        return
        
    await query.answer()
    
    data = query.data
    if data.startswith("topic_"):
        topic = data.replace("topic_", "", 1)
        await query.edit_message_text(f"'{topic}' mavzusi tanlandi. Test boshlanmoqda...")
        await start_test_for_topic(query.message.chat_id, topic, context)

async def start_test_for_topic(chat_id, topic, context: ContextTypes.DEFAULT_TYPE):
    questions = db.get_questions_by_topic(topic)
    if not questions:
        await context.bot.send_message(chat_id=chat_id, text=f"'{topic}' mavzusida savollar topilmadi.")
        return
        
    # Bor barcha savollarni tasodifiy tartibda aralashtirib beramiz
    selected_questions = random.sample(questions, len(questions))
        
    # Testni fonga yuboramiz (asyncio.create_task)
    context.application.create_task(run_test_loop(chat_id, topic, selected_questions, context))

async def run_test_loop(chat_id, topic, questions, context: ContextTypes.DEFAULT_TYPE):
    for i, q in enumerate(questions):
        # q = (id, text, option1, option2, option3, correct_option)
        q_id, q_text, opt1, opt2, opt3, correct_idx = q
        options = [opt1, opt2, opt3]
        
        msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"[{i+1}/{len(questions)}] {q_text}",
            options=options,
            type="quiz",
            correct_option_id=correct_idx,
            is_anonymous=False,
            open_period=20
        )
        
        poll_id = msg.poll.id
        db.add_active_poll(poll_id, chat_id, q_id, correct_idx)
        
        # Keyingi savolgacha 20 soniya kutamiz
        await asyncio.sleep(20)
        
        # Test muddati tugagach poll yopib qo'yilishi mumkin, lekin API orqali poll stop qilsa bo'ladi:
        try:
            await context.bot.stop_poll(chat_id, msg.message_id)
        except Exception as e:
            logger.warning(f"Poll stop qilishda xatolik: {e}")
            
        # Bazadan olib tashlaymiz
        db.remove_active_poll(poll_id)
        
    # Test tugagach qisqacha reyting chiqaramiz
    rating = db.get_chat_rating(chat_id, topic)
    text = f"Test yakunlandi!\nMavzu: {topic}\n\nTop ishtirokchilar:\n"
    
    top_user = None
    top_score_text = ""
    
    if not rating:
        text += "Hech kim qatnashmadi."
    else:
        for idx, row in enumerate(rating):
            # row: (username, correct_count, total_count)
            text += f"{idx+1}. {row[0] or 'NoName'} - {row[1]}/{row[2]}\n"
            if idx == 0 and row[1] > 0:
                top_user = row[0] or 'NoName'
                top_score_text = f"{row[1]}/{row[2]}"
            if idx == 2: # Faqat top 3 ni ko'rsatamiz qisqacha reytingda
                break
                
    await context.bot.send_message(chat_id=chat_id, text=text)

    # Agar g'olib bo'lsa (hech bo'lmasa bitta to'g'ri topgan bo'lsa), sertifikat beramiz
    if top_user:
        try:
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            
            img = Image.new('RGB', (800, 600), color=(255, 250, 240))
            d = ImageDraw.Draw(img)
            
            d.rectangle([20, 20, 780, 580], outline=(218, 165, 32), width=10)
            d.rectangle([30, 30, 770, 570], outline=(218, 165, 32), width=2)
            
            try:
                font_large = ImageFont.truetype("Roboto-Bold.ttf", 60)
                font_med = ImageFont.truetype("Roboto-Bold.ttf", 40)
                font_small = ImageFont.truetype("Roboto-Bold.ttf", 30)
            except:
                font_large = font_med = font_small = ImageFont.load_default()
                
            d.text((400, 150), "FAXRIIY YORLIQ", fill=(218, 165, 32), font=font_large, anchor="mm")
            d.text((400, 250), "Ushbu yorliq", fill=(50, 50, 50), font=font_small, anchor="mm")
            d.text((400, 320), top_user, fill=(0, 0, 100), font=font_large, anchor="mm")
            d.text((400, 420), f"'{topic}' mavzusida {top_score_text} ball bilan\nbirinchi o'rinni egallagani uchun berildi.", fill=(50, 50, 50), font=font_med, anchor="mm", align="center")
            
            bio = BytesIO()
            bio.name = 'sertifikat.jpg'
            img.save(bio, 'JPEG')
            bio.seek(0)
            
            await context.bot.send_photo(chat_id=chat_id, photo=bio, caption=f"🏆 Boshqalar uchun ham zo'r namuna, tabriklaymiz {top_user}!")
        except Exception as e:
            logger.error(f"Sertifikat yaratishda xatolik: {e}")

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user
    selected_option = answer.option_ids[0] if answer.option_ids else -1
    
    active_poll = db.get_active_poll(poll_id)
    if not active_poll:
        return
        
    chat_id, question_id, correct_option = active_poll
    is_correct = (selected_option == correct_option)
    
    # Bazadan savolni mavzusini olishimiz kerak
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT topic FROM questions WHERE id = ?", (question_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return
    topic = row[0]
    
    # Natijani saqlaymiz
    db.update_user_result(chat_id, user.id, user.first_name or user.username or "User", topic, is_correct)
