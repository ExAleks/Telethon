"""
proxy.py — SOCKS5 / MTProto прокси для Telethon.
"""
import re
from dataclasses import dataclass

_PROXY_RE = re.compile(
    r'^(socks5|socks4|http)://(?:([^:]+):([^@]+)@)?([^:/]+):(\d+)$', re.I,
)


@dataclass
class Socks5Proxy:
    host: str
    port: int
    user: str = ''
    password: str = ''

    def as_dict(self) -> dict:
        d = {'proxy_type': 'socks5', 'addr': self.host, 'port': self.port}
        if self.user:
            d['username'] = self.user
        if self.password:
            d['password'] = self.password
        return d


@dataclass
class MtprotoProxy:
    server: str
    port: int
    secret: str

    def as_tuple(self) -> tuple:
        return (self.server, self.port, self.secret)


def parse_proxy_url(url: str) -> Socks5Proxy | None:
    """socks5://user:pass@host:port"""
    m = _PROXY_RE.match(url.strip())
    if not m:
        return None
    _, user, pwd, host, port = m.groups()
    return Socks5Proxy(host=host, port=int(port), user=user or '', password=pwd or '')


def socks5(host: str, port: int = 1080, user: str = '', password: str = '') -> Socks5Proxy:
    return Socks5Proxy(host=host, port=port, user=user, password=password)


def mtproto(server: str, port: int = 443, secret: str = '') -> MtprotoProxy:
    return MtprotoProxy(server=server, port=port, secret=secret)
