import time
import logging
import serial
import re
from collections import deque

logger = logging.getLogger('modem')

class Modem:
    """Improved Modem helper:
    - initializes modem in text mode
    - supports reading via AT+CMGL (list) and parsing +CMT/+CMTI URC events
    - provides a simple FIFO buffer for unsolicited lines
    Note: some modems behave differently; this aims to be robust for common USB 4G dongles.
    """
    CMGL_RE = re.compile(r'^\+CMGL: *(?P<index>\d+),"(?P<stat>[^"]+)","(?P<sender>[^"]*)"')
    CMT_RE = re.compile(r'^\+CMT: ?"?(?P<sender>[+\d]*)"?.*')
    CMTI_RE = re.compile(r'^\+CMTI: "(?P<mem>\w+)",(?P<index>\d+)')

    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._buffer = deque()

    def open(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(0.5)
        self._init_modem()
        # flush any initial URC
        self._drain()

    def _init_modem(self):
        # Ensure text mode and set CNMI to receive indications
        self._safe_at('AT')
        self._safe_at('ATE0')  # no echo
        self._safe_at('AT+CMGF=1')  # text mode
        # CNMI: route new message indications as unsolicited +CMTI
        self._safe_at('AT+CNMI=2,1,0,0,0')

    def _safe_at(self, cmd, wait=0.2):
        try:
            return self.run_at(cmd, wait=wait, read_lines=8)
        except Exception as e:
            logger.warning('AT cmd failed (%s): %s', cmd, e)
            return []

    def run_at(self, cmd, wait=0.2, read_lines=8):
        if not self.ser:
            raise RuntimeError('Serial not opened')
        cmd_str = cmd.strip() + '\r'
        # write
        self.ser.write(cmd_str.encode())
        time.sleep(wait)
        out = []
        for _ in range(read_lines):
            line = self.ser.readline()
            if not line:
                break
            try:
                decoded = line.decode(errors='ignore').strip()
            except Exception:
                decoded = str(line)
            if decoded:
                out.append(decoded)
        logger.debug('AT %s -> %s', cmd, out)
        return out

    def _drain(self, timeout=0.1):
        # read any immediate lines and push to buffer
        if not self.ser:
            return
        self.ser.timeout = timeout
        try:
            while True:
                line = self.ser.readline()
                if not line:
                    break
                try:
                    decoded = line.decode(errors='ignore').strip()
                except Exception:
                    decoded = str(line)
                if decoded:
                    self._buffer.append(decoded)
        finally:
            self.ser.timeout = self.timeout

    def _read_buffered(self):
        # collect buffered lines into a list
        out = []
        while self._buffer:
            out.append(self._buffer.popleft())
        return out

    def list_unread(self):
        """Primary method to get unread SMS messages.
        Strategy:
        1. Drain buffer and look for +CMT or +CMTI events and fetch where needed.
        2. If none, query AT+CMGL="REC UNREAD" and parse.
        Returns list of dicts: {'remote':..., 'content':...}
        """
        results = []
        # Step 1: drain serial into buffer
        self._drain()
        lines = list(self._read_buffered())

        # parse unsolicited lines first
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('+CMT:'):
                # next line is content
                m = self.CMT_RE.match(line)
                sender = m.group('sender') if m else 'unknown'
                content = lines[i+1] if i+1 < len(lines) else ''
                results.append({'remote': sender, 'content': content})
                i += 2
                continue
            if line.startswith('+CMTI:'):
                m = self.CMTI_RE.match(line)
                if m:
                    idx = m.group('index')
                    # try to read specific index
                    try:
                        those = self.run_at(f'AT+CMGR={idx}', wait=0.3, read_lines=20)
                        # parse CMGR response
                        parsed = self._parse_cmgr(those)
                        if parsed:
                            results.extend(parsed)
                    except Exception:
                        logger.exception('Failed to fetch CMGR for %s', idx)
                i += 1
                continue
            i += 1

        # Step 2: if still empty, try CMGL for REC UNREAD
        if not results:
            try:
                lines = self.run_at('AT+CMGL="REC UNREAD"', wait=0.5, read_lines=80)
                parsed = self._parse_cmgl(lines)
                results.extend(parsed)
            except Exception:
                logger.exception('AT+CMGL failed')

        # Final: return unique results
        # (de-dup by (remote, content))
        seen = set()
        uniq = []
        for r in results:
            key = (r.get('remote'), r.get('content'))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        return uniq

    def _parse_cmgr(self, lines):
        # parse output of AT+CMGR (single message)
        out = []
        i = 0
        while i < len(lines):
            l = lines[i]
            if l.startswith('+CMGR:'):
                parts = l.split('"')
                sender = parts[1] if len(parts) > 1 else 'unknown'
                content = lines[i+1] if i+1 < len(lines) else ''
                out.append({'remote': sender, 'content': content})
                i += 2
            else:
                i += 1
        return out

    def _parse_cmgl(self, lines):
        out = []
        i = 0
        while i < len(lines):
            l = lines[i]
            if l.startswith('+CMGL:'):
                # attempt to extract sender robustly
                m = self.CMGL_RE.match(l)
                if m:
                    sender = m.group('sender')
                else:
                    # fallback: look for quoted phone number
                    parts = l.split('"')
                    sender = parts[3] if len(parts) > 3 else 'unknown'
                content = lines[i+1] if i+1 < len(lines) else ''
                out.append({'remote': sender, 'content': content})
                i += 2
            else:
                i += 1
        return out

    def send_sms(self, number, text):
        self._safe_at('AT+CMGF=1')
        cmd = f'AT+CMGS="{number}"'
        if not self.ser:
            raise RuntimeError('Serial not opened')
        # write command
        self.ser.write((cmd + '\r').encode())
        time.sleep(0.5)
        # write content
        self.ser.write((text + chr(26)).encode())
        time.sleep(1)
        out = []
        # read responses until OK or timeout
        deadline = time.time() + 5
        while time.time() < deadline:
            line = self.ser.readline()
            if not line:
                break
            try:
                decoded = line.decode(errors='ignore').strip()
            except Exception:
                decoded = str(line)
            if decoded:
                out.append(decoded)
                if decoded.upper().startswith('OK') or '+CMGS:' in decoded or 'ERROR' in decoded:
                    break
        return out

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
