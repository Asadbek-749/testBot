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
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("Sizda bu buyruqni ishlatish uchun ruxsat yo'q. Faqatgina adminlar testni boshlay oladi.")
        return

    # Agar guruhda bo'lmasa, ogohlantirish (xohlasangiz olib tashlash mumkin)
    if update.effective_chat.type == "private":
        await update.message.reply_text("Ushbu buyruqni guruhlarda ishlatganingiz ma'qul, lekin bu yerda ham ishlatsa bo'ladi.")
    
    # Agar /test <mavzu> yozilgan bo'lsa
    if context.args:
        topic = " ".join(context.args)
        await start_test_for_topic(update.effective_chat.id, topic, context, update.message.message_thread_id)
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
    if not db.is_admin(query.from_user.id):
        await query.answer("Sizda test boshlash uchun ruxsat yo'q.", show_alert=True)
        return
        
    await query.answer()
    
    try:
        data = query.data
        if data.startswith("topic_"):
            topic = data.replace("topic_", "", 1)
            await query.edit_message_text(f"'{topic}' mavzusi tanlandi. Test boshlanmoqda...")
            thread_id = query.message.message_thread_id
            await start_test_for_topic(query.message.chat_id, topic, context, thread_id)
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Callback Xato: {str(e)}")

async def start_test_for_topic(chat_id, topic, context: ContextTypes.DEFAULT_TYPE, thread_id=None):
    questions = db.get_questions_by_topic(topic)
    if not questions:
        await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text=f"'{topic}' mavzusida savollar topilmadi.")
        return
        
    # Bor barcha savollarni tasodifiy tartibda aralashtirib beramiz
    selected_questions = random.sample(questions, len(questions))
        
    # Testni fonga yuboramiz (asyncio.create_task)
    context.application.create_task(run_test_loop(chat_id, topic, selected_questions, context, thread_id))

async def run_test_loop(chat_id, topic, questions, context: ContextTypes.DEFAULT_TYPE, thread_id=None):
    try:
        poll_message_ids = []
        
        for i, q in enumerate(questions):
            q_id, q_text, opt1, opt2, opt3, correct_idx = q
            options = [opt1, opt2, opt3]
            
            msg = await context.bot.send_poll(
                chat_id=chat_id,
                message_thread_id=thread_id,
                question=f"[{i+1}/{len(questions)}] {q_text}",
                options=options,
                type="quiz",
                correct_option_id=correct_idx,
                is_anonymous=False,
                open_period=20
            )
            
            poll_message_ids.append(msg.message_id)
            poll_id = msg.poll.id
            db.add_active_poll(poll_id, chat_id, q_id, correct_idx)
            
            await asyncio.sleep(20)
            
            try:
                await context.bot.stop_poll(chat_id, msg.message_id)
            except Exception as e:
                logger.warning(f"Poll stop qilishda xatolik: {e}")
                
            db.remove_active_poll(poll_id)
            
        rating = db.get_chat_rating(chat_id, topic)
        text = f"Test yakunlandi!\nMavzu: {topic}\n\nTop ishtirokchilar:\n"
        
        top_user = None
        top_score_text = ""
        
        if not rating:
            text += "Hech kim qatnashmadi."
        else:
            for idx, row in enumerate(rating):
                text += f"{idx+1}. {row[0] or 'NoName'} - {row[1]}/{row[2]}\n"
                if idx == 0 and row[1] > 0:
                    top_user = row[0] or 'NoName'
                    top_score_text = f"{row[1]}/{row[2]}"
                if idx == 2:
                    break
                    
        await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text=text)
    
        if top_user:
            try:
                from PIL import Image, ImageDraw, ImageFont
                from io import BytesIO
                import urllib.request
                import os
                
                font_path = "Roboto-Bold.ttf"
                if not os.path.exists(font_path):
                    try:
                        url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
                        urllib.request.urlretrieve(url, font_path)
                    except Exception as e:
                        pass
                
                template_path = "template.jpg"
                
                font_clean = "font_clean.ttf"
                if not os.path.exists(font_clean):
                    try:
                        url = "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf"
                        urllib.request.urlretrieve(url, font_clean)
                    except Exception as e:
                        pass
                
                if os.path.exists(template_path):
                    img = Image.open(template_path).convert('RGB')
                    d = ImageDraw.Draw(img)
                    width, height = img.size
                    
                    center_rect = [width*0.15, height*0.22, width*0.85, height*0.65]
                    d.rectangle(center_rect, fill=(253, 250, 240))
                    
                    d.rectangle([width*0.15, height*0.68, width*0.85, height*0.82], fill=(253, 250, 240))
                    
                else:
                    img = Image.new('RGB', (1000, 700), color=(253, 250, 240))
                    d = ImageDraw.Draw(img)
                    d.rectangle([30, 30, 970, 670], outline=(212, 175, 55), width=15)
                    width, height = 1000, 700
                
                try:
                    font_title = ImageFont.truetype(font_clean, int(height*0.09))
                    font_name = ImageFont.truetype(font_clean, int(height*0.11))
                    font_text = ImageFont.truetype(font_clean, int(height*0.035))
                    font_small = ImageFont.truetype(font_clean, int(height*0.03))
                except:
                    font_title = font_name = font_text = font_small = ImageFont.load_default()
                    
                d.text((width/2, height*0.28), "SERTIFIKAT", fill=(212, 175, 55), font=font_title, anchor="mm")
                d.text((width/2, height*0.37), "Ushbu sertifikat", fill=(26, 43, 76), font=font_text, anchor="mm")
                
                d.text((width/2, height*0.48), top_user, fill=(212, 175, 55), font=font_name, anchor="mm")
                
                desc_text = f"«{topic}» testini muvaffaqiyatli yechib,\n1-o'rinni egallaganingiz uchun taqdim etiladi."
                d.text((width/2, height*0.58), desc_text, fill=(26, 43, 76), font=font_text, anchor="mm", align="center")
                
                import datetime
                date_str = datetime.datetime.now().strftime("%d.%m.%Y")
                
                d.text((width*0.3, height*0.72), "NATIJA", fill=(26, 43, 76), font=font_small, anchor="mm", align="center")
                d.text((width*0.3, height*0.77), f"{top_score_text}", fill=(212, 175, 55), font=font_text, anchor="mm", align="center")
                
                d.text((width*0.5, height*0.72), "SANA", fill=(26, 43, 76), font=font_small, anchor="mm", align="center")
                d.text((width*0.5, height*0.77), f"{date_str}", fill=(212, 175, 55), font=font_text, anchor="mm", align="center")
                
                d.text((width*0.7, height*0.72), "O'RIN", fill=(26, 43, 76), font=font_small, anchor="mm", align="center")
                d.text((width*0.7, height*0.77), "1-O'RIN", fill=(212, 175, 55), font=font_text, anchor="mm", align="center")
                
                bio = BytesIO()
                bio.name = 'sertifikat.jpg'
                img.save(bio, 'JPEG')
                bio.seek(0)
                
                await context.bot.send_photo(chat_id=chat_id, message_thread_id=thread_id, photo=bio, caption=f"🏆 Boshqalar uchun ham zo'r namuna, tabriklaymiz {top_user}!")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"Sertifikat xato: {str(e)}")
                
        if context.job_queue:
            context.job_queue.run_once(
                delete_polls_job,
                120,
                data={'chat_id': chat_id, 'message_ids': poll_message_ids}
            )
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Test Loop Xato: {str(e)}")

async def delete_polls_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data['chat_id']
    message_ids = job.data['message_ids']
    
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass

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
