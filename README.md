# Telethon

**[English](#english) | [Русский](#русский)**

---

## Русский

Готовая болванка для Telegram-клиента на **Telethon**. Подключай к любому проекту — боту, парсеру, автопостингу, чему угодно.

### Возможности

- **Авторизация** — по телефону + код, двухфакторная аутентификация (2FA), QR-код
- **Прокси** — SOCKS5, MTProto, автоматический fallback (SOCKS5 → MTProto → direct)
- **Админы** — проверка прав через `ADMIN_IDS` в `.env`
- **Логи** — SQLite-таблица `logs`, функция `add_log()`
- **Настройки** — универсальное хранилище `get_setting()` / `set_setting()`
- **Сессии** — `StringSession` в БД, автоматическое восстановление
- **Веб-панель** — Flask-админка: дашборд, авторизация, прокси, логи, настройки

### Быстрый старт

```bash
git clone https://github.com/ExAleks/Telethon.git
cd Telethon
pip install -r requirements.txt
cp .env.example .env
# заполни API_ID, API_HASH, PHONE в .env
python run.py              # интерактивное меню
python run.py --web        # веб-панель на http://localhost:5000
python run.py --web --port=8080  # свой порт
```

### Использование в коде

```python
from Telethon import TelethonClient, login, qr_login, poll_qr, is_admin
from Telethon.proxy import socks5, mtproto

# Подключение (context manager)
async with TelethonClient() as tc:
    me = await tc.client.get_me()

# С прокси
s5 = socks5('host', 1080, 'user', 'pass')
async with TelethonClient(socks5_proxy=s5) as tc:
    me = await tc.client.get_me()

# Авторизация по телефону
ok, msg, status = await login(api_id, api_hash, phone)
if status == 'need_code':
    ok, msg, _ = await login(api_id, api_hash, phone, code='12345')
if status == 'need_password':
    ok, msg, _ = await login(api_id, api_hash, phone, password='2fa')

# Авторизация по QR
token = qr_login(api_id, api_hash)
state = poll_qr(token)  # {'status': 'waiting', 'url': '...'}
```

### Структура

```
Telethon/
├── __init__.py    — экспорт API
├── config.py      — .env + дефолты
├── database.py    — SQLite: настройки, логи
├── proxy.py       — SOCKS5 / MTProto
├── client.py      — TelethonClient с fallback
├── auth.py        — вход: телефон, QR, 2FA
├── utils.py       — is_admin(), парсинг ссылок
├── web.py         — Flask веб-панель
├── run.py         — интерактивное меню / веб
├── templates/     — HTML-шаблоны
├── static/        — CSS
└── .env.example   — шаблон переменных
```

---

## English

Ready-to-use boilerplate for a Telegram client built on **Telethon**. Drop it into any project — bots, parsers, auto-posting, anything.

### Features

- **Authorization** — phone + code, two-factor authentication (2FA), QR code login
- **Proxy support** — SOCKS5, MTProto, automatic fallback (SOCKS5 → MTProto → direct)
- **Admin check** — user role validation via `ADMIN_IDS` in `.env`
- **Logging** — SQLite `logs` table, `add_log()` function
- **Settings** — universal key-value store `get_setting()` / `set_setting()`
- **Sessions** — `StringSession` stored in DB, automatic recovery
- **Web panel** — Flask admin: dashboard, auth, proxy, logs, settings

### Quick start

```bash
git clone https://github.com/ExAleks/Telethon.git
cd Telethon
pip install -r requirements.txt
cp .env.example .env
# fill in API_ID, API_HASH, PHONE in .env
python run.py              # interactive menu
python run.py --web        # web panel at http://localhost:5000
python run.py --web --port=8080  # custom port
```

### Usage

```python
from Telethon import TelethonClient, login, qr_login, poll_qr, is_admin
from Telethon.proxy import socks5, mtproto

# Connect (context manager)
async with TelethonClient() as tc:
    me = await tc.client.get_me()

# With proxy
s5 = socks5('host', 1080, 'user', 'pass')
async with TelethonClient(socks5_proxy=s5) as tc:
    me = await tc.client.get_me()

# Phone login
ok, msg, status = await login(api_id, api_hash, phone)
if status == 'need_code':
    ok, msg, _ = await login(api_id, api_hash, phone, code='12345')
if status == 'need_password':
    ok, msg, _ = await login(api_id, api_hash, phone, password='2fa')

# QR login
token = qr_login(api_id, api_hash)
state = poll_qr(token)  # {'status': 'waiting', 'url': '...'}
```

### Structure

```
Telethon/
├── __init__.py    — API export
├── config.py      — .env + defaults
├── database.py    — SQLite: settings, logs
├── proxy.py       — SOCKS5 / MTProto
├── client.py      — TelethonClient with fallback
├── auth.py        — login: phone, QR, 2FA
├── utils.py       — is_admin(), link parsing
├── web.py         — Flask web panel
├── run.py         — interactive menu / web
├── templates/     — HTML templates
├── static/        — CSS
└── .env.example   — env template
```

### License

MIT
