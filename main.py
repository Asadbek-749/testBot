import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, MessageHandler, filters
from config import BOT_TOKEN
import database as db

from handlers.admin import (
    add_question_handler, list_questions, delete_question, import_excel, admin_stats, schedule_test,
    add_admin_command, del_admin_command
)
from handlers.test import start_test_command, topic_callback, poll_answer_handler
from handlers.stats import mystats, rating, rating_callback

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    # Ma'lumotlar bazasini initsializatsiya qilamiz
    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # Admin buyruqlari
    application.add_handler(add_question_handler)
    application.add_handler(CommandHandler('list_questions', list_questions))
    application.add_handler(CommandHandler('delete_question', delete_question))
    application.add_handler(CommandHandler('stats', admin_stats))
    application.add_handler(CommandHandler('schedule_test', schedule_test))
    application.add_handler(MessageHandler(filters.Document.ALL, import_excel))
    application.add_handler(CommandHandler("addadmin", add_admin_command))
    application.add_handler(CommandHandler("deladmin", del_admin_command))

    # Test buyruqlari
    application.add_handler(CommandHandler('test', start_test_command))
    application.add_handler(CallbackQueryHandler(topic_callback))
    application.add_handler(PollAnswerHandler(poll_answer_handler))

    # Statistika buyruqlari
    application.add_handler(CommandHandler('mystats', mystats))
    application.add_handler(CommandHandler('rating', rating))
    application.add_handler(CallbackQueryHandler(rating_callback, pattern="^rating_"))

    logger.info("Bot ishga tushmoqda...")
    application.run_polling()

if __name__ == '__main__':
    main()
