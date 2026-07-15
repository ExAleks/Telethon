"""
client.py — TelegramClient с прокси и fallback.
"""
import asyncio

from telethon import TelegramClient, connection
from telethon.sessions import StringSession

from proxy import Socks5Proxy, MtprotoProxy


class TelethonClient:
    """Обёртка над TelegramClient с автоматическим прокси и fallback."""

    def __init__(
        self,
        session=None,
        api_id: int | None = None,
        api_hash: str | None = None,
        socks5_proxy: Socks5Proxy | None = None,
        mtproto_proxy: MtprotoProxy | None = None,
    ):
        from config import API_ID, API_HASH
        self.api_id = api_id or API_ID
        self.api_hash = api_hash or API_HASH
        self.session = session or StringSession()
        self.socks5 = socks5_proxy
        self.mtproto = mtproto_proxy
        self._client: TelegramClient | None = None

    def _build(self, session=None, socks: Socks5Proxy | None = None,
               mtproto_: MtprotoProxy | None = None) -> TelegramClient:
        sess = session or self.session
        if socks:
            return TelegramClient(sess, self.api_id, self.api_hash, proxy=socks.as_dict())
        if mtproto_:
            return TelegramClient(
                sess, self.api_id, self.api_hash,
                connection=connection.ConnectionTcpMTProxyRandomizedIntermediate,
                proxy=mtproto_.as_tuple(),
            )
        return TelegramClient(sess, self.api_id, self.api_hash)

    async def connect(self, timeout: float = 20) -> TelegramClient:
        """Подключение с fallback: SOCKS5 → MTProto → direct."""
        attempts = []
        if self.socks5:
            attempts.append(('socks5', self.socks5))
        if self.mtproto:
            attempts.append(('mtproto', self.mtproto))
        attempts.append(('direct', None))

        last_err = None
        for kind, data in attempts:
            try:
                client = self._build(socks=data if kind == 'socks5' else None,
                                     mtproto_=data if kind == 'mtproto' else None)
                await asyncio.wait_for(client.connect(), timeout=timeout)
                if client.is_connected():
                    self._client = client
                    return client
            except Exception as e:
                last_err = e
                try:
                    if client.is_connected():
                        await client.disconnect()
                except Exception:
                    pass

        raise ConnectionError(f'Не удалось подключиться: {last_err}')

    async def disconnect(self):
        if self._client and self._client.is_connected():
            await self._client.disconnect()
        self._client = None

    @property
    def client(self) -> TelegramClient:
        if not self._client:
            raise RuntimeError('Клиент не подключён. Вызовите await client.connect()')
        return self._client

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()
