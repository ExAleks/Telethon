"""
utils.py — Минимальные утилиты.
"""
import re
from config import ADMIN_IDS

_TG_LINK_RE = re.compile(
    r'server=([^&]+)&port=(\d+)&secret=([0-9a-fA-F]+)', re.I,
)
_V2RAY_RE = re.compile(r'(vless|vmess|trojan|ss)://[^\s\'"<>]+', re.I)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def parse_tg_link(link: str) -> tuple[str | None, int | None, str | None]:
    """tg://proxy?server=...&port=...&secret=... → (server, port, secret)."""
    m = _TG_LINK_RE.search(link)
    if not m:
        return None, None, None
    return m.group(1), int(m.group(2)), m.group(3)


def parse_proxy_link(link: str) -> dict | None:
    """socks5://user:pass@host:port → dict."""
    from proxy import parse_proxy_url
    p = parse_proxy_url(link)
    return p.as_dict() if p else None


def extract_v2ray(text: str) -> list[str]:
    return _V2RAY_RE.findall(text or '')


def format_mtproto_link(server: str, port: int, secret: str) -> str:
    return f'tg://proxy?server={server}&port={port}&secret={secret}'
