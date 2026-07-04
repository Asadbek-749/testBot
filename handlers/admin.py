import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from config import ADMIN_IDS
import database as db
import openpyxl
from io import BytesIO

logger = logging.getLogger(__name__)

# States
ASK_TEXT, ASK_OPT1, ASK_OPT2, ASK_OPT3, ASK_CORRECT, ASK_TOPIC = range(6)

async def check_admin(update: Update):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return False
    return True

async def add_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Yangi savol qo'shishni boshlaymiz.\nIltimos, savol matnini yuboring:\n(Bekor qilish uchun /cancel deb yozing)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_TEXT

async def add_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['q_text'] = update.message.text
    await update.message.reply_text("Yaxshi. Endi 1-variantni yuboring:")
    return ASK_OPT1

async def add_question_opt1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opt1'] = update.message.text
    await update.message.reply_text("2-variantni yuboring:")
    return ASK_OPT2

async def add_question_opt2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opt2'] = update.message.text
    await update.message.reply_text("3-variantni yuboring:")
    return ASK_OPT3

async def add_question_opt3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['opt3'] = update.message.text
    
    reply_keyboard = [['1', '2', '3']]
    await update.message.reply_text(
        "Variantlar qabul qilindi. Qaysi biri to'g'ri javob? (Tugmalardan birini tanlang)",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_CORRECT

async def add_question_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text not in ['1', '2', '3']:
        await update.message.reply_text("Iltimos, 1, 2 yoki 3 tugmasini bosing.")
        return ASK_CORRECT
    
    # 0-indexed correct option (0, 1, 2)
    context.user_data['correct'] = int(text) - 1
    
    await update.message.reply_text(
        "Endi ushbu savol qaysi mavzuga tegishli ekanini yozing (masalan: 'MS Word', 'Internet va xavfsizlik'):",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_TOPIC

async def add_question_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = update.message.text
    
    q_text = context.user_data['q_text']
    opt1 = context.user_data['opt1']
    opt2 = context.user_data['opt2']
    opt3 = context.user_data['opt3']
    correct = context.user_data['correct']
    
    db.add_question(q_text, opt1, opt2, opt3, correct, topic)
    
    await update.message.reply_text(f"Savol muvaffaqiyatli saqlandi!\nMavzu: {topic}")
    context.user_data.clear()
    return ConversationHandler.END

async def add_question_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Savol qo'shish bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return
    
    questions = db.get_all_questions()
    if not questions:
        await update.message.reply_text("Hozircha savollar yo'q.")
        return
    
    text = "Savollar ro'yxati:\n\n"
    for q in questions:
        # q: (id, text, topic)
        line = f"ID: {q[0]} | Mavzu: {q[2]} | {q[1][:30]}...\n"
        if len(text) + len(line) > 4000:
            await update.message.reply_text(text)
            text = ""
        text += line
        
    if text:
        await update.message.reply_text(text)

async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return
    
    if not context.args:
        await update.message.reply_text("Iltimos, o'chirmoqchi bo'lgan savol ID sini yozing. Masalan: /delete_question 5")
        return
    
    q_id_str = context.args[0]
    if not q_id_str.isdigit():
        await update.message.reply_text("ID raqam bo'lishi kerak.")
        return
    
    q_id = int(q_id_str)
    if db.delete_question(q_id):
        await update.message.reply_text(f"ID {q_id} bo'lgan savol o'chirildi.")
    else:
        await update.message.reply_text("Bunday ID ga ega savol topilmadi.")

async def import_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return
        
    document = update.message.document
    if not document.file_name.endswith('.xlsx'):
        await update.message.reply_text("Iltimos, faqat .xlsx (Excel) formatidagi fayl yuklang.")
        return
        
    await update.message.reply_text("Fayl qabul qilindi. Yuklanmoqda...")
    
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes))
        sheet = wb.active
        
        count = 0
        # 1-qatorni sarlavha deb hisoblaymiz, 2-qatordan o'qiymiz
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
                
            # Ustunlar: Savol, Opt1, Opt2, Opt3, Correct(1,2,3), Topic
            if len(row) >= 6:
                q_text, opt1, opt2, opt3, correct_val, topic = row[:6]
                
                try:
                    correct_idx = int(correct_val) - 1
                    if correct_idx not in [0, 1, 2]:
                        continue
                    db.add_question(str(q_text), str(opt1), str(opt2), str(opt3), correct_idx, str(topic))
                    count += 1
                except (ValueError, TypeError):
                    continue
                    
        await update.message.reply_text(f"Muvaffaqiyatli! Jami {count} ta savol bazaga qo'shildi.")
    except Exception as e:
        logger.error(f"Excel o'qishda xatolik: {e}")
        await update.message.reply_text("Faylni o'qishda xatolik yuz berdi. Fayl strukturasi to'g'riligini tekshiring.")


add_question_handler = ConversationHandler(
    entry_points=[CommandHandler('add_question', add_question_start)],
    states={
        ASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_text)],
        ASK_OPT1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_opt1)],
        ASK_OPT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_opt2)],
        ASK_OPT3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_opt3)],
        ASK_CORRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_correct)],
        ASK_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_question_topic)],
    },
    fallbacks=[CommandHandler('cancel', add_question_cancel)]
)
