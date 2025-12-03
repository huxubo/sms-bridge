from flask import Flask, Response, request, jsonify, render_template
import logging
from .config import load_config
from .db import DB
from .forwarder import Forwarder
from .worker import Worker
from .keepalive import KeepAlive
from functools import wraps

app = Flask(__name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)

cfg = load_config()
db = DB(cfg.get('database', '/data/smsbridge.db'))
forwarder = Forwarder(cfg)
worker = Worker(cfg, db, forwarder)
keepalive = KeepAlive(worker.modem, cfg, db, forwarder)


def require_basic_auth(fn):
    """Protect endpoints with optional HTTP Basic auth configured in http.auth_user/http.auth_password."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_user = cfg.get('http', {}).get('auth_user')
        auth_password = cfg.get('http', {}).get('auth_password')
        if auth_user and auth_password:
            auth = request.authorization
            if not auth or auth.username != auth_user or auth.password != auth_password:
                return Response('Authentication required', 401, headers={'WWW-Authenticate': 'Basic realm="SMS-Bridge"'})
        return fn(*args, **kwargs)

    return wrapper

@app.route('/')
@require_basic_auth
def index():
    messages = db.get_messages(100)
    return render_template('index.html', messages=messages, cfg=cfg)


@app.route('/_messages_json')
@require_basic_auth
def messages_json():
    """Return recent messages for the polling UI."""
    limit = request.args.get('limit', default=100, type=int)
    limit = max(1, min(limit, 500))
    messages = db.get_messages(limit)
    return jsonify({"messages": messages})


@app.route('/start', methods=['POST'])
@require_basic_auth
def start():
    try:
        worker.start()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/stop', methods=['POST'])
@require_basic_auth
def stop():
    worker.stop()
    return jsonify({'ok': True})

@app.route('/keepalive', methods=['POST'])
@require_basic_auth
def do_keepalive():
    res = keepalive.send_keepalive()
    return jsonify(res)


@app.route('/status')
@require_basic_auth
def status():
    """Return worker running state and last poll time."""
    return jsonify(worker.status())

@app.route('/send', methods=['POST'])
@require_basic_auth
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
