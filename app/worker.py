import time
import threading
import logging
from datetime import datetime
from .modem import Modem

logger = logging.getLogger('worker')

class Worker:
    def __init__(self, cfg, db, forwarder):
        self.cfg = cfg
        self.db = db
        self.forwarder = forwarder
        self.modem = Modem(cfg['serial_port'], cfg.get('baudrate', 115200))
        self.poll_interval = cfg.get('poll_interval', 8)
        self.running = False
        self.thread = None
        self.last_polled_at = None

    def start(self):
        if self.running:
            logger.info('Worker already running')
            return
        self.running = True
        self.modem.open()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info('Worker started')

    def stop(self):
        if not self.running:
            logger.info('Worker already stopped')
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.modem.close()
        self.forwarder.shutdown()
        logger.info('Worker stopped')

    def status(self):
        return {
            'running': self.running,
            'poll_interval': self.poll_interval,
            'last_polled_at': self.last_polled_at.isoformat() if self.last_polled_at else None,
        }

    def _run(self):
        while self.running:
            try:
                messages = self.modem.list_unread()
                for m in messages:
                    remote = m.get('remote')
                    content = m.get('content')
                    logger.info('Got SMS from %s: %s', remote, content)
                    self.db.insert_message(remote, content, 'in')
                    self.forwarder.forward(remote, content)
                self.last_polled_at = datetime.utcnow()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.exception('Error while polling modem: %s', e)
                time.sleep(5)
