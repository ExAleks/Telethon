"""
web.py — Flask-веб-панель: дашборд, авторизация, прокси, логи, настройки.
"""
import asyncio
import os
import time

from flask import Flask, render_template, request, redirect, url_for, flash

from config import API_ID, API_HASH, PHONE, SOCKS5_HOST, SOCKS5_PORT, SOCKS5_USER, SOCKS5_PASSWORD
from config import MTPROTO_SERVER, MTPROTO_PORT, MTPROTO_SECRET
from database import init_db, get_config, update_config, get_setting, set_setting, add_log
from auth import login, qr_login, poll_qr, normalize_credentials
from client import TelethonClient
from proxy import socks5, mtproto
from utils import is_admin

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()


def _run(coro):
    return asyncio.run(coro)


# ---- Дашборд ----

@app.route('/')
def dashboard():
    cfg = get_config()
    authorized = bool(cfg.get('session_string') and not cfg.get('phone_code_hash'))
    return render_template('dashboard.html',
                           authorized=authorized, config=cfg,
                           socks5_host=SOCKS5_HOST, mtproto_server=MTPROTO_SERVER)


# ---- Авторизация ----

@app.route('/auth', methods=['GET', 'POST'])
def auth_page():
    cfg = get_config()
    authorized = bool(cfg.get('session_string') and not cfg.get('phone_code_hash'))
    pending = bool(cfg.get('phone_code_hash'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_code':
            api_id = request.form.get('api_id', '').strip()
            api_hash = request.form.get('api_hash', '').strip()
            phone = request.form.get('phone', '').strip()
            try:
                aid, ahash, ph = normalize_credentials(api_id, api_hash, phone)
            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('auth_page'))
            ok, msg, status = _run(login(aid, ahash, ph))
            flash(msg, 'success' if ok else 'error')
            if status == 'need_code':
                return redirect(url_for('auth_page'))
            return redirect(url_for('auth_page'))

        if action == 'confirm_code':
            api_id = cfg.get('api_id') or API_ID
            api_hash = cfg.get('api_hash') or API_HASH
            phone = cfg.get('phone') or PHONE
            code = request.form.get('code', '').strip()
            if not code:
                flash('Введите код', 'error')
                return redirect(url_for('auth_page'))
            ok, msg, status = _run(login(api_id, api_hash, phone, code=code))
            flash(msg, 'success' if ok else 'error')
            if status == 'need_password':
                return redirect(url_for('auth_page'))
            return redirect(url_for('auth_page'))

        if action == 'confirm_2fa':
            api_id = cfg.get('api_id') or API_ID
            api_hash = cfg.get('api_hash') or API_HASH
            phone = cfg.get('phone') or PHONE
            password = request.form.get('password', '').strip()
            if not password:
                flash('Введите пароль 2FA', 'error')
                return redirect(url_for('auth_page'))
            ok, msg, _ = _run(login(api_id, api_hash, phone, password=password))
            flash(msg, 'success' if ok else 'error')
            return redirect(url_for('auth_page'))

        if action == 'logout':
            update_config(api_id=None, api_hash=None, phone=None,
                          session_string=None, phone_code_hash=None, enabled=0)
            flash('Выход выполнен', 'success')
            return redirect(url_for('auth_page'))

        if action == 'qr_start':
            api_id = request.form.get('api_id', '').strip() or str(API_ID)
            api_hash = request.form.get('api_hash', '').strip() or API_HASH
            try:
                aid, ahash, _ = normalize_credentials(api_id, api_hash, '0000000000')
            except ValueError as e:
                flash(str(e), 'error')
                return redirect(url_for('auth_page'))
            token = qr_login(aid, ahash)
            set_setting('qr_token', token)
            flash('QR-логин запущен', 'success')
            return redirect(url_for('auth_page'))

        if action == 'qr_poll':
            token = get_setting('qr_token')
            if not token:
                flash('Нет активного QR', 'error')
                return redirect(url_for('auth_page'))
            state = poll_qr(token)
            if state['status'] == 'done':
                ss = state.get('session_string')
                if ss:
                    update_config(api_id=cfg.get('api_id'), api_hash=cfg.get('api_hash'),
                                  phone='QR', session_string=ss, phone_code_hash=None, enabled=1)
                flash('QR-авторизация успешна!', 'success')
                return redirect(url_for('auth_page'))
            elif state['status'] == 'need_password':
                flash('Требуется 2FA пароль', 'error')
            elif state['status'] == 'waiting':
                flash(f'QR URL: {state.get("url", "")}', 'success')
            else:
                flash(f'QR: {state["status"]}', 'error')
            return redirect(url_for('auth_page'))

    qr_token = get_setting('qr_token')
    qr_state = poll_qr(qr_token) if qr_token else None
    return render_template('auth.html', config=cfg, authorized=authorized,
                           pending=pending, qr_state=qr_state)


# ---- Прокси ----

@app.route('/proxy', methods=['GET', 'POST'])
def proxy_page():
    if request.method == 'POST':
        set_setting('socks5_host', request.form.get('socks5_host', '').strip())
        set_setting('socks5_port', request.form.get('socks5_port', '1080').strip())
        set_setting('socks5_user', request.form.get('socks5_user', '').strip())
        pw = request.form.get('socks5_password', '').strip()
        if pw:
            set_setting('socks5_password', pw)
        set_setting('mtproto_server', request.form.get('mtproto_server', '').strip())
        set_setting('mtproto_port', request.form.get('mtproto_port', '443').strip())
        set_setting('mtproto_secret', request.form.get('mtproto_secret', '').strip())
        flash('Прокси сохранены', 'success')
        return redirect(url_for('proxy_page'))

    return render_template('proxy.html',
        socks5_host=get_setting('socks5_host', SOCKS5_HOST),
        socks5_port=get_setting('socks5_port', str(SOCKS5_PORT)),
        socks5_user=get_setting('socks5_user', SOCKS5_USER),
        socks5_password=get_setting('socks5_password', SOCKS5_PASSWORD),
        mtproto_server=get_setting('mtproto_server', MTPROTO_SERVER),
        mtproto_port=get_setting('mtproto_port', str(MTPROTO_PORT)),
        mtproto_secret=get_setting('mtproto_secret', MTPROTO_SECRET),
    )


# ---- Тест подключения ----

@app.route('/test')
def test_connection():
    cfg = get_config()
    if not cfg.get('session_string'):
        flash('Сначала авторизуйтесь', 'error')
        return redirect(url_for('auth_page'))

    s5_host = get_setting('socks5_host', SOCKS5_HOST)
    s5_port = int(get_setting('socks5_port', str(SOCKS5_PORT)))
    s5_user = get_setting('socks5_user', SOCKS5_USER)
    s5_pass = get_setting('socks5_password', SOCKS5_PASSWORD)
    mt_server = get_setting('mtproto_server', MTPROTO_SERVER)
    mt_port = int(get_setting('mtproto_port', str(MTPROTO_PORT)))
    mt_secret = get_setting('mtproto_secret', MTPROTO_SECRET)

    s5 = socks5(s5_host, s5_port, s5_user, s5_pass) if s5_host else None
    mt = mtproto(mt_server, mt_port, mt_secret) if mt_server else None

    from telethon.sessions import StringSession

    async def _go():
        tc = TelethonClient(session=StringSession(cfg['session_string']),
                            api_id=cfg['api_id'], api_hash=cfg['api_hash'],
                            socks5_proxy=s5, mtproto_proxy=mt)
        client = await tc.connect()
        me = await client.get_me()
        await tc.disconnect()
        return me

    try:
        me = _run(_go())
        flash(f'OK: {me.first_name} (@{me.username})', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('dashboard'))


# ---- Логи ----

@app.route('/logs')
def logs_page():
    from database import _open
    conn = _open()
    rows = conn.execute('SELECT level, message, created_at FROM logs ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    return render_template('logs.html', logs=rows)


# ---- Настройки ----

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        update_config(enabled=request.form.get('enabled') == '1')
        set_setting('admin_password', request.form.get('admin_password', '').strip())
        flash('Настройки сохранены', 'success')
        return redirect(url_for('settings_page'))

    cfg = get_config()
    return render_template('settings.html', config=cfg,
                           admin_password=get_setting('admin_password', ''))


def run_web(host='0.0.0.0', port=5000, debug=False):
    init_db()
    add_log('INFO', f'Веб-панель запущена: http://{host}:{port}')
    app.run(host=host, port=port, debug=debug)
