"""
run.py — Интерактивное меню: авторизация, статус, быстрый старт.
"""
from config import API_ID, API_HASH, PHONE
from database import init_db, get_config, update_config, add_log
from auth import login, qr_login, poll_qr, normalize_credentials
from client import TelethonClient
from proxy import socks5, mtproto
from utils import is_admin


def _status():
    init_db()
    cfg = get_config()
    print()
    if cfg.get('session_string') and not cfg.get('phone_code_hash'):
        print(f'  Авторизован: {cfg.get("phone") or "?"}')
    elif cfg.get('phone_code_hash'):
        print(f'  Ожидание кода: {cfg.get("phone")}')
    else:
        print('  Не авторизован')
    print(f'  API ID: {cfg.get("api_id") or "(нет)"}')
    print()


def _auth_menu():
    api_id = input(f'  API ID [{API_ID}]: ').strip() or str(API_ID)
    api_hash = input(f'  API Hash [{API_HASH}]: ').strip() or API_HASH
    phone = input(f'  Телефон [{PHONE}]: ').strip() or PHONE

    try:
        aid, ahash, ph = normalize_credentials(api_id, api_hash, phone)
    except ValueError as e:
        print(f'  Ошибка: {e}')
        return

    print('  Отправка кода...')
    ok, msg, status = asyncio_run(login(aid, ahash, ph))
    print(f'  {msg}')

    if status == 'need_code':
        code = input('  Код: ').strip()
        if code:
            ok, msg, _ = asyncio_run(login(aid, ahash, ph, code=code))
            print(f'  {msg}')

    if status == 'need_password':
        pwd = input('  Пароль 2FA: ').strip()
        if pwd:
            ok, msg, _ = asyncio_run(login(aid, ahash, ph, password=pwd))
            print(f'  {msg}')


def _qr_menu():
    import time as _time
    api_id = input(f'  API ID [{API_ID}]: ').strip() or str(API_ID)
    api_hash = input(f'  API Hash [{API_HASH}]: ').strip() or API_HASH

    try:
        aid, ahash, _ = normalize_credentials(api_id, api_hash, '0000000000')
    except ValueError as e:
        print(f'  Ошибка: {e}')
        return

    print('  Запуск QR-логина...')
    token = qr_login(aid, ahash)

    while True:
        state = poll_qr(token)
        status = state['status']

        if status == 'connecting':
            print('  Подключение...', end='\r')
            _time.sleep(1)
            continue

        if status == 'waiting':
            url = state.get('url', '')
            print(f'\n  Отсканируйте QR в Telegram:')
            print(f'  {url}')
            print(f'  (обновляется автоматически, таймаут 3 мин)\n')

            while True:
                _time.sleep(3)
                s = poll_qr(token)
                if s['status'] != 'waiting':
                    state = s
                    break
            status = state['status']

        if status == 'done':
            ss = state.get('session_string')
            if ss:
                update_config(api_id=aid, api_hash=ahash, phone='QR',
                              session_string=ss, phone_code_hash=None, enabled=1)
                add_log('INFO', 'QR-авторизация успешна')
                print('  Авторизация успешна!')
            return

        if status == 'need_password':
            pwd = input('  Пароль 2FA: ').strip()
            if pwd:
                ss = state.get('partial_session')
                if ss:
                    update_config(session_string=ss)
                ok, msg, _ = asyncio_run(login(aid, ahash, '0000000000', password=pwd))
                print(f'  {msg}')
            return

        if status == 'timeout':
            print('  Таймаут. Попробуйте снова.')
            return

        if status == 'error':
            print(f'  Ошибка: {state.get("error")}')
            return

        if status == 'not_found':
            print('  Токен не найден')
            return


def _test_connect():
    cfg = get_config()
    if not cfg.get('session_string'):
        print('  Сначала авторизуйтесь')
        return
    print('  Подключение...')
    from telethon.sessions import StringSession
    from config import SOCKS5_HOST, SOCKS5_PORT, SOCKS5_USER, SOCKS5_PASSWORD
    from config import MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET

    s5 = socks5(SOCKS5_HOST, SOCKS5_PORT, SOCKS5_USER, SOCKS5_PASSWORD) if SOCKS5_HOST else None
    mt = mtproto(MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET) if MTPROTO_SERVER else None

    async def _go():
        tc = TelethonClient(session=StringSession(cfg['session_string']),
                            api_id=cfg['api_id'], api_hash=cfg['api_hash'],
                            socks5_proxy=s5, mtproto_proxy=mt)
        client = await tc.connect()
        me = await client.get_me()
        await tc.disconnect()
        return me

    try:
        me = asyncio_run(_go())
        print(f'  OK: {me.first_name} (@{me.username})')
    except Exception as e:
        print(f'  Ошибка: {e}')


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


def main():
    init_db()
    print('\n=== Telethon ===')
    _status()

    while True:
        print('1) Статус')
        print('2) Авторизация (телефон + код)')
        print('3) Авторизация (QR-код)')
        print('4) Тест подключения')
        print('0) Выход')
        choice = input('\n> ').strip()

        if choice == '1':
            _status()
        elif choice == '2':
            _auth_menu()
        elif choice == '3':
            _qr_menu()
        elif choice == '4':
            _test_connect()
        elif choice == '0':
            break


if __name__ == '__main__':
    import sys
    if '--web' in sys.argv:
        from web import run_web
        port = 5000
        for a in sys.argv:
            if a.startswith('--port='):
                port = int(a.split('=')[1])
        run_web(port=port, debug='--debug' in sys.argv)
    else:
        main()
