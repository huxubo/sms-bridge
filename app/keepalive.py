class KeepAlive:
    def __init__(self, modem, cfg, db, forwarder):
        self.modem = modem
        self.cfg = cfg
        self.db = db
        self.forwarder = forwarder

    def send_keepalive(self):
        if not self.cfg.get('keepalive', {}).get('enabled'):
            return {'ok': False, 'reason': 'keepalive disabled'}
        number = self.cfg['keepalive']['number']
        message = self.cfg['keepalive'].get('message', 'OK')
        out = self.modem.send_sms(number, message)
        self.db.insert_message(number, message, 'out')
        return {'ok': True, 'raw': out}
