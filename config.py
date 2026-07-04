import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = []
_admin_ids_str = os.getenv("ADMIN_IDS", "")
if _admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip().isdigit()]

DATABASE_URL = os.getenv("DATABASE_URL", "")
