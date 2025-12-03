import logging
from concurrent.futures import ThreadPoolExecutor

import requests

logger = logging.getLogger('forwarder')

class Forwarder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.timeout = cfg.get('request_timeout', 10)
        self._max_workers = cfg.get('forwarder_workers', 4)
        self.executor = ThreadPoolExecutor(max_workers=self._max_workers)

    def shutdown(self):
        """Stop background workers used for asynchronous forwarding."""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None

    def _ensure_executor(self):
        """Create a new executor when the previous one has been shut down."""
        if self.executor is None or getattr(self.executor, "_shutdown", False):
            self.executor = ThreadPoolExecutor(max_workers=self._max_workers)

    def send_telegram(self, remote, content):
        if not self.cfg.get('telegram', {}).get('enabled'):
            return
        token = self.cfg['telegram']['bot_token']
        chat_id = self.cfg['telegram']['chat_id']
        text = f"📩 From: {remote}\n{content}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=self.timeout)
        logger.info('Telegram status: %s', resp.status_code)
        return resp.json()

    def send_pushplus(self, remote, content):
        if not self.cfg.get('wechat_pushplus', {}).get('enabled'):
            return
        token = self.cfg['wechat_pushplus']['token']
        title = f"SMS from {remote}"
        body = content
        url = 'http://www.pushplus.plus/send'
        resp = requests.post(url, json={"token": token, "title": title, "content": body}, timeout=self.timeout)
        logger.info('PushPlus status: %s', resp.status_code)
        return resp.json()

    def forward(self, remote, content):
        """Dispatch forwarding tasks asynchronously to avoid blocking polling."""

        self._ensure_executor()

        def _forward_all():
            try:
                self.send_telegram(remote, content)
                self.send_pushplus(remote, content)
            except Exception:
                logger.exception("Forwarding failed for %s", remote)

        self.executor.submit(_forward_all)
