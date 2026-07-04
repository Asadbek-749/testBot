# Telegram Test Bot

Bu "Kompyuter Savodxonligi" o'quv markazi uchun test o'tkazishni avtomatlashtiruvchi Telegram bot.

## O'rnatish (Local muhitda)

1. Repozitoriyni yuklab oling.
2. Virtual muhit (virtualenv) yarating:
   ```bash
   python -m venv venv
   source venv/bin/activate # (Linux/Mac)
   venv\Scripts\activate # (Windows)
   ```
3. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
4. `.env` faylini yarating (`.env.example` dan nusxa olib) va ichiga bot tokeningiz hamda adminlarning Telegram ID raqamlarini yozing:
   ```env
   BOT_TOKEN=SizningTokeningiz
   ADMIN_IDS=123456789,987654321
   ```
5. Botni ishga tushiring:
   ```bash
   python main.py
   ```

## Railway.app ga deploy qilish

1. Loyihani GitHub ga yuklang.
2. Railway.app da yangi loyiha oching va "Deploy from GitHub repo" ni tanlang.
3. Loyiha sozlamalaridagi "Variables" (Yoki Environment Variables) bo'limida quyidagilarni qo'shing:
   - `BOT_TOKEN`
   - `ADMIN_IDS` (vergul bilan ajratib, masalan: 12345,67890)
4. Railway `Procfile` ni o'zi topadi va worker sifatida `python main.py` ni ishga tushiradi. Agar bot ishga tushmasa, "Settings" -> "Start Command" ga qarang. (U yerda default buyruqni `python main.py` qilib qo'yishingiz ham mumkin).

## Ishlatish
- Faqat adminlar:
  - `/add_question` - savol qo'shish
  - `/list_questions` - savollar ro'yxati
  - `/delete_question <id>` - savolni o'chirish
- Guruhlarda:
  - `/test` - faqat adminlar testni boshlashi mumkin
  - `/rating` - shu guruh bo'yicha reytingni ko'rish
- Shaxsiy (botga to'g'ridan to'g'ri yozganda):
  - `/mystats` - o'z statistikasini ko'rish
