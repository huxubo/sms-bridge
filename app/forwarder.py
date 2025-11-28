import requests
import logging

logger = logging.getLogger('forwarder')

class Forwarder:
    def __init__(self, cfg):
        self.cfg = cfg

    def send_telegram(self, remote, content):
        if not self.cfg.get('telegram', {}).get('enabled'):
            return
        token = self.cfg['telegram']['bot_token']
        chat_id = self.cfg['telegram']['chat_id']
        text = f"📩 From: {remote}\n{content}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text})
        logger.info('Telegram status: %s', resp.status_code)
        return resp.json()

    def send_pushplus(self, remote, content):
        if not self.cfg.get('wechat_pushplus', {}).get('enabled'):
            return
        token = self.cfg['wechat_pushplus']['token']
        title = f"SMS from {remote}"
        body = content
        url = 'http://www.pushplus.plus/send'
        resp = requests.post(url, json={"token": token, "title": title, "content": body})
        logger.info('PushPlus status: %s', resp.status_code)
        return resp.json()

    def forward(self, remote, content):
        self.send_telegram(remote, content)
        self.send_pushplus(remote, content)
