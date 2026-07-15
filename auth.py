"""
auth.py — Авторизация Telethon: телефон + код, 2FA.
"""
import asyncio
import re
import threading
import uuid

from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError, ApiIdInvalidError

from config import SESSION_FILE
from client import TelethonClient
from database import get_config, update_config, add_log


def normalize_credentials(api_id, api_hash, phone) -> tuple[int, str, str]:
    api_id_str = str(api_id or '').strip()
    api_hash_str = str(api_hash or '').strip().strip('"').strip("'")
    phone_str = str(phone or '').strip().replace(' ', '').replace('-', '')

    if not api_id_str.isdigit():
        raise ValueError('API ID должен быть числом')
    aid = int(api_id_str)
    if aid <= 0:
        raise ValueError('API ID > 0')
    if not re.fullmatch(r'[a-fA-F0-9]{32}', api_hash_str):
        raise ValueError('API Hash — ровно 32 hex-символа')
    if not phone_str.startswith('+'):
        phone_str = '+' + phone_str if phone_str.isdigit() else phone_str
    return aid, api_hash_str, phone_str


async def login(
    api_id: int,
    api_hash: str,
    phone: str,
    code: str | None = None,
    password: str | None = None,
    socks5=None,
    mtproto=None,
) -> tuple[bool, str, str | None]:
    """
    Авторизация.
    code=None, password=None → отправка кода
    code=... → подтверждение кода
    password=... → 2FA
    """
    try:
        api_id, api_hash, phone = normalize_credentials(api_id, api_hash, phone)
    except ValueError as e:
        return False, str(e), 'error'

    tc = TelethonClient(api_id=api_id, api_hash=api_hash, socks5_proxy=socks5, mtproto_proxy=mtproto)

    try:
        if code is None and password is None:
            update_config(api_id=api_id, api_hash=api_hash, phone=phone,
                          session_string=None, phone_code_hash=None, enabled=0)
            client = await tc.connect()
            if await client.is_user_authorized():
                return await _finalize(tc, client, api_id, api_hash, phone)

            sent = await client.send_code_request(phone)
            code_hash = getattr(sent, 'phone_code_hash', None)
            partial = StringSession.save(client.session)
            update_config(phone_code_hash=code_hash, session_string=partial)
            return False, 'Код отправлен. Введите его.', 'need_code'

        cfg = get_config()
        if not cfg.get('session_string'):
            return False, 'Сначала отправьте код', 'error'

        tc2 = TelethonClient(
            session=StringSession(cfg['session_string']),
            api_id=api_id, api_hash=api_hash, socks5_proxy=socks5, mtproto_proxy=mtproto,
        )
        client = await tc2.connect()
        code_hash = cfg.get('phone_code_hash')

        if password is not None:
            await client.sign_in(password=password)
        elif code is not None:
            await client.sign_in(phone, code, phone_code_hash=code_hash)

        if await client.is_user_authorized():
            return await _finalize(tc2, client, api_id, api_hash, phone)
        return False, 'Авторизация не завершена', None

    except ApiIdInvalidError:
        return False, 'API ID / API Hash неверны', 'error'
    except SessionPasswordNeededError:
        partial = StringSession.save(client.session)
        update_config(session_string=partial)
        return False, 'Требуется 2FA пароль', 'need_password'
    except FloodWaitError as e:
        return False, f'Подождите {e.seconds // 60} мин.', None
    except Exception as e:
        return False, str(e), None
    finally:
        await tc.disconnect()
        try:
            await tc2.disconnect()
        except Exception:
            pass


async def _finalize(tc, client, api_id, api_hash, phone):
    session_string = StringSession.save(client.session)
    update_config(api_id=api_id, api_hash=api_hash, phone=phone,
                  session_string=session_string, phone_code_hash=None, enabled=1)
    add_log('INFO', f'Авторизован: {phone}')
    await tc.disconnect()
    return True, f'OK: {phone}', None


# ---- QR-логин ----

_qr_states: dict[str, dict] = {}
_qr_lock = threading.Lock()


def _qr_worker(api_id, api_hash, token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        tc = TelethonClient(api_id=api_id, api_hash=api_hash)
        try:
            client = await tc.connect()
        except Exception as e:
            with _qr_lock:
                _qr_states[token]['error'] = str(e)
            return

        try:
            qr = await asyncio.wait_for(client.qr_login(), timeout=20)
        except Exception as e:
            with _qr_lock:
                _qr_states[token]['error'] = str(e)
            await tc.disconnect()
            return

        with _qr_lock:
            _qr_states[token]['url'] = qr.url
            _qr_states[token]['ready'] = True

        try:
            await qr.wait(timeout=180)
        except SessionPasswordNeededError:
            partial = StringSession.save(client.session)
            with _qr_lock:
                _qr_states[token]['partial_session'] = partial
                _qr_states[token]['need_password'] = True
            return
        except asyncio.TimeoutError:
            with _qr_lock:
                _qr_states[token]['error'] = 'timeout'
            return

        if await client.is_user_authorized():
            ss = StringSession.save(client.session)
            with _qr_lock:
                _qr_states[token]['session_string'] = ss
                _qr_states[token]['done'] = True
        else:
            with _qr_lock:
                _qr_states[token]['error'] = 'not authorized'
        await tc.disconnect()

    try:
        loop.run_until_complete(_run())
    except Exception as e:
        with _qr_lock:
            _qr_states[token]['error'] = str(e)


def qr_login(api_id: int, api_hash: str) -> str:
    """Запуск QR-логина. Возвращает token."""
    token = uuid.uuid4().hex[:16]
    with _qr_lock:
        _qr_states[token] = {
            'url': None, 'ready': False, 'done': False,
            'error': None, 'session_string': None,
            'need_password': False, 'partial_session': None,
        }
    t = threading.Thread(target=_qr_worker, args=(api_id, api_hash, token), daemon=True)
    t.start()
    return token


def poll_qr(token: str) -> dict:
    """Статус QR-логина."""
    with _qr_lock:
        s = _qr_states.get(token)
    if not s:
        return {'status': 'not_found'}
    if s['need_password']:
        return {'status': 'need_password', 'partial_session': s['partial_session']}
    if s['error'] == 'timeout':
        return {'status': 'timeout'}
    if s['error']:
        return {'status': 'error', 'error': s['error']}
    if s['done']:
        return {'status': 'done', 'session_string': s['session_string']}
    if s['ready'] and s['url']:
        return {'status': 'waiting', 'url': s['url']}
    return {'status': 'connecting'}
