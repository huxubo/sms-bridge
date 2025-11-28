from flask import Flask, request, jsonify, render_template
import logging
from .config import load_config
from .db import DB
from .forwarder import Forwarder
from .worker import Worker
from .keepalive import KeepAlive

app = Flask(__name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)

cfg = load_config()
db = DB(cfg.get('database', '/data/smsbridge.db'))
forwarder = Forwarder(cfg)
worker = Worker(cfg, db, forwarder)
keepalive = KeepAlive(worker.modem, cfg, db, forwarder)

@app.route('/')
def index():
    messages = db.get_messages(100)
    return render_template('index.html', messages=messages, cfg=cfg)

@app.route('/start', methods=['POST'])
def start():
    try:
        worker.start()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/stop', methods=['POST'])
def stop():
    worker.stop()
    return jsonify({'ok': True})

@app.route('/keepalive', methods=['POST'])
def do_keepalive():
    res = keepalive.send_keepalive()
    return jsonify(res)

@app.route('/send', methods=['POST'])
def send_sms():
    data = request.json or {}
    number = data.get('number')
    text = data.get('text')
    if not number or not text:
        return jsonify({'ok': False, 'error': 'number and text required'})
    out = worker.modem.send_sms(number, text)
    db.insert_message(number, text, 'out')
    return jsonify({'ok': True, 'raw': out})

if __name__ == '__main__':
    app.run(host=cfg['http']['host'], port=cfg['http']['port'])
