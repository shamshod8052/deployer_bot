# Deployer Bot

Telegram orqali yuborilgan **zip fayl** ichidagi bot loyihalarni avtomatik **serverga deploy qiluvchi** yordamchi bot.

## ✨ Xususiyatlari
- Telegram orqali zip fayl yuborish orqali deploy qilish
- Docker yordamida har bir botni alohida konteynerda ishga tushirish
- Default `Dockerfile` yaratib berish (agar mavjud bo‘lmasa)
- `/list` komandasi orqali ishlayotgan botlarni ko‘rish
- `/stop` komandasi orqali kerakli botni to‘xtatish

## ⚙️ O‘rnatish
```bash
git clone git@github.com:shamshod8052/deployer_bot.git
cd deployer_bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
````

## 🔑 Sozlash

`.env` fayl ichida:

```env
BOT_TOKEN=abs
ADMINS=1013305,82091
```

## 🚀 Ishga tushirish

```bash
python bot.py
```

Zo‘r, endi o‘quvchilarga aniq qoidalar qo‘yib berish kerak ✅ — ular qanday qilib **zip faylni tayyorlashlari** haqida. Buni `README.md` ichiga “📦 Zip fayl talablari” qismi sifatida qo‘shib berish mumkin.

---

## 📦 Zip fayl talablari

Bot loyihasini yuborishda quyidagi qoidalarga amal qilinishi shart:

1. **Fayllar ildizda bo‘lishi kerak**
   Zip ichida qo‘shimcha papka bo‘lmasin. To‘g‘ri ko‘rinish:

   ```
   1-dars.zip
    ├── bot.py
    ├── requirements.txt
    └── .env   (ixtiyoriy)
   ```

   ❌ Noto‘g‘ri:

   ```
   1-dars.zip
    └── 1-dars/
         ├── bot.py
         └── requirements.txt
   ```

2. **Majburiy fayllar**:

   * `bot.py` – asosiy bot kodi (`asyncio.run(main())` bilan tugashi kerak).
   * `requirements.txt` – kerakli kutubxonalar ro‘yxati (`aiogram`, `python-dotenv` va boshqalar).

3. **Ixtiyoriy fayllar**:

   * `.env` – agar token yoki boshqa sozlamalarni saqlash kerak bo‘lsa.
     Masalan:

     ```
     BOT_TOKEN=123456:ABCDEF
     ```

4. **Tokenni koding ichida yozmang!**
   Token faqat `.env` faylda bo‘lishi kerak. `bot.py` ichida esa:

   ```python
   import os
   from aiogram import Bot, Dispatcher
   import asyncio
   from dotenv import load_dotenv

   load_dotenv()
   TOKEN = os.getenv("BOT_TOKEN")

   async def main():
       bot = Bot(token=TOKEN)
       dp = Dispatcher()
       await dp.start_polling(bot)

   if __name__ == "__main__":
       asyncio.run(main())
   ```

5. **Dockerfile qo‘shish shart emas**, deployer bot avtomatik yaratadi. Lekin xohlasa, quyidagi minimal `Dockerfile` ni qo‘shishlari mumkin:

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY . /app
   RUN pip install --no-cache-dir -r requirements.txt
   CMD ["python", "bot.py"]
   ```
---

✍️ Author: [Shamshod Ramazonov](https://github.com/shamshod8052)
