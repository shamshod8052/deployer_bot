```markdown
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

---

✍️ Author: [Shamshod Ramazonov](https://github.com/shamshod8052)

```
