# -*- coding: utf-8 -*-
"""키보드 활성화·확인창 초점·파일 입력 실측 도구 (2026-09-06 · CI 미등재 · 장부 audit/REFERRER_A11Y_2026-09-06.md §7).

왜: 앱 안 브라우저 창은 Enter/Space 의 keypress 를 못 보내 활성화를 잴 수 없었다(v231 장부). 여기서는 **격리된 Chrome/Edge**
    (임시 user-data-dir · headless · 사용자 프로필·탭·저장값 무접촉)을 DevTools 프로토콜로 직접 몰아 **실제 키 이벤트**만 보낸다.
    DOM `.click()`·합성 이벤트는 쓰지 않는다. 초점 「위치」를 잡을 때도 실제 Tab 키로 이동한다(예외는 --site 의 setup 표시 항목).
    파일은 자동화 API(`DOM.setFileInputFiles`)로 넣는다 — OS 파일 선택창의 키보드 조작과는 별개로 기록한다.

실행: python audit/kb_keyboard_check.py --control            # 대조 페이지(순수 button·link·input·summary·range)로 하네스 검증
      python audit/kb_keyboard_check.py --site [--root <저장소>]   # 대조 통과 뒤 세 화면의 빠진 경로만
      [--browser <exe>] [--out <json>] [--headed]
의존: 표준 라이브러리만(웹소켓 클라이언트 내장). Chrome 또는 Edge 가 설치돼 있어야 한다.
"""
import argparse
import base64
import http.server
import io
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)
BROWSERS = [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
            '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge']


# ---------------------------------------------------------------- 최소 웹소켓 클라이언트(RFC 6455 · 텍스트 프레임)
class WS:
    def __init__(self, url):
        assert url.startswith('ws://')
        rest = url[5:]
        hostport, _, path = rest.partition('/')
        host, _, port = hostport.partition(':')
        self.sock = socket.create_connection((host, int(port or 80)), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ('GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (path, hostport, key))
        self.sock.sendall(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError('websocket handshake failed')
            buf += chunk
        head, _, rest = buf.partition(b'\r\n\r\n')
        if b' 101 ' not in head.split(b'\r\n')[0]:
            raise RuntimeError('websocket upgrade refused: %r' % head[:120])
        self.buf = rest

    def _readn(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError('websocket closed')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode('utf-8')
        mask = os.urandom(4)
        n = len(data)
        head = bytes([0x81])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack('>H', n)
        else:
            head += bytes([0x80 | 127]) + struct.pack('>Q', n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(head + mask + masked)

    def recv(self):
        msg = b''
        while True:
            b0, b1 = self._readn(2)
            fin, op = b0 & 0x80, b0 & 0x0f
            n = b1 & 0x7f
            if n == 126:
                n = struct.unpack('>H', self._readn(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._readn(8))[0]
            if b1 & 0x80:
                mask = self._readn(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._readn(n)))
            else:
                payload = self._readn(n)
            if op == 0x8:
                raise RuntimeError('websocket close frame')
            if op == 0x9:
                self.sock.sendall(bytes([0x8A, 0x80 | len(payload)]) + b'\x00\x00\x00\x00' + payload)
                continue
            if op == 0xA:
                continue
            msg += payload
            if fin:
                return msg.decode('utf-8')


# ---------------------------------------------------------------- CDP
class CDP:
    def __init__(self, ws_url):
        self.ws = WS(ws_url)
        self.n = 0
        self.events = []

    def call(self, method, params=None, timeout=30):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
        t0 = time.time()
        while True:
            m = json.loads(self.ws.recv())
            if m.get('id') == mid:
                if 'error' in m:
                    raise RuntimeError('%s: %s' % (method, m['error']))
                return m.get('result', {})
            if 'method' in m:
                self.events.append(m)
            if time.time() - t0 > timeout:
                raise TimeoutError(method)

    def wait_event(self, name, timeout=15):
        t0 = time.time()
        while True:
            for i, e in enumerate(self.events):
                if e['method'] == name:
                    return self.events.pop(i)
            self.ws.sock.settimeout(max(0.1, timeout - (time.time() - t0)))
            try:
                m = json.loads(self.ws.recv())
            except (socket.timeout, TimeoutError):
                self.ws.sock.settimeout(60)
                raise TimeoutError(name)
            self.ws.sock.settimeout(60)
            if 'method' in m:
                self.events.append(m)
            if time.time() - t0 > timeout:
                raise TimeoutError(name)

    def has_event(self, name):
        return any(e['method'] == name for e in self.events)

    def drain(self, name):
        got = [e for e in self.events if e['method'] == name]
        self.events = [e for e in self.events if e['method'] != name]
        return got

    def eval(self, js, await_promise=False):
        r = self.call('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': await_promise})
        if 'exceptionDetails' in r:
            raise RuntimeError('JS: %s' % r['exceptionDetails'].get('exception', {}).get('description', r['exceptionDetails']))
        return r.get('result', {}).get('value')

    def object_id(self, js):
        r = self.call('Runtime.evaluate', {'expression': js})
        return r['result']['objectId']

    KEYS = {'Tab': ('Tab', 'Tab', 9, None), 'Enter': ('Enter', 'Enter', 13, '\r'), 'Space': (' ', 'Space', 32, ' '),
            'ArrowRight': ('ArrowRight', 'ArrowRight', 39, None), 'ArrowLeft': ('ArrowLeft', 'ArrowLeft', 37, None),
            'Escape': ('Escape', 'Escape', 27, None)}

    def key(self, name, shift=False):
        k, code, vk, text = self.KEYS[name]
        base = {'key': k, 'code': code, 'windowsVirtualKeyCode': vk, 'nativeVirtualKeyCode': vk, 'modifiers': 8 if shift else 0}
        down = dict(base, type='keyDown' if text else 'rawKeyDown')
        if text:
            down['text'] = text
            down['unmodifiedText'] = text
        self.call('Input.dispatchKeyEvent', down)
        self.call('Input.dispatchKeyEvent', dict(base, type='keyUp'))

    def type_text(self, s):
        self.call('Input.insertText', {'text': s})

    def navigate(self, url):
        self.drain('Page.loadEventFired')
        self.call('Page.navigate', {'url': url})
        self.wait_event('Page.loadEventFired', 30)

    def active(self):
        return self.eval("(()=>{const e=document.activeElement; if(!e) return 'none'; const r=e.getBoundingClientRect();"
                         "return e.tagName.toLowerCase()+'#'+(e.id||(typeof e.className==='string'?e.className.split(' ')[0]:''))"
                         "+'|'+(e.getAttribute('aria-label')||e.textContent||e.value||'').trim().replace(/\\s+/g,' ').slice(0,20)"
                         "+'|'+Math.round(r.width)+'x'+Math.round(r.height);})()")

    def tab_until(self, predicate_js, limit=60):
        """실제 Tab 키로 이동하며 predicate(document.activeElement) 가 참이 될 때까지. 누른 횟수를 돌려준다(-1 = 못 찾음)."""
        for i in range(1, limit + 1):
            self.key('Tab')
            if self.eval('(function(e){ return !!(%s); })(document.activeElement)' % predicate_js):
                return i
        return -1


# ---------------------------------------------------------------- 브라우저·서버
def find_browser(explicit=None):
    for p in ([explicit] if explicit else []) + BROWSERS:
        if p and os.path.exists(p):
            return p
    raise SystemExit('Chrome/Edge 실행 파일을 찾지 못했다 — --browser <exe>')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Browser:
    def __init__(self, exe, headed=False):
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix='kbchk_profile_')
        args = [exe, '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.profile, '--no-first-run',
                '--no-default-browser-check', '--disable-extensions', '--disable-background-networking', '--disable-sync',
                '--window-size=1200,900', '--remote-allow-origins=*', 'about:blank']
        if not headed:
            args.insert(1, '--headless=new')
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                v = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json/version' % self.port, timeout=2).read())
                self.version = v.get('Browser', '?')
                break
            except Exception:
                time.sleep(0.2)
        else:
            self.close()
            raise SystemExit('브라우저 DevTools 포트가 열리지 않았다')

    def page(self):
        for _ in range(50):
            lst = json.loads(urllib.request.urlopen('http://127.0.0.1:%d/json/list' % self.port, timeout=5).read())
            pages = [t for t in lst if t.get('type') == 'page']
            if pages:
                c = CDP(pages[0]['webSocketDebuggerUrl'])
                c.call('Page.enable'); c.call('Runtime.enable'); c.call('DOM.enable')
                c.call('Emulation.setFocusEmulationEnabled', {'enabled': True})
                return c
            time.sleep(0.2)
        raise SystemExit('페이지 타깃 없음')

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        shutil.rmtree(self.profile, ignore_errors=True)


class Static:
    def __init__(self, directory):
        self.port = free_port()
        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=directory, **k)
        handler_cls = type('H', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None,
                           '__init__': lambda s, *a, **k: http.server.SimpleHTTPRequestHandler.__init__(s, *a, directory=directory, **k)})
        srv_cls = type('S', (http.server.ThreadingHTTPServer,), {'handle_error': lambda *a: None})   # 브라우저가 끊은 연결의 스택 소음 제거
        self.srv = srv_cls(('127.0.0.1', self.port), handler_cls)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def url(self, path):
        return 'http://127.0.0.1:%d/%s' % (self.port, path)

    def close(self):
        self.srv.shutdown()


# ---------------------------------------------------------------- 보고
class Report:
    def __init__(self):
        self.rows = []

    def add(self, case, desc, ok, actual='', kind='실측'):
        self.rows.append(dict(case=case, desc=desc, ok=bool(ok), actual=str(actual), kind=kind))
        print(('  OK   ' if ok else '  DIFF ') + '[%s] %s — %s' % (case, desc, actual))

    def fails(self):
        return [r for r in self.rows if not r['ok']]


CONTROL_HTML = """<!doctype html><meta charset="utf-8"><title>kb control</title>
<body>
<button id="b" type="button">button</button>
<a id="l" href="#anchor">link</a>
<input id="i" type="text" value="">
<details id="d"><summary id="s">summary</summary><p>body</p></details>
<input id="r" type="range" min="0" max="10" value="0">
<input id="f" type="file">
<p id="anchor">anchor</p>
<script>
window.C={b:0,l:0,f:0,i:0};
document.getElementById('b').addEventListener('click',()=>C.b++);
document.getElementById('l').addEventListener('click',e=>{C.l++; e.preventDefault();});
document.getElementById('i').addEventListener('keydown',e=>{ if(e.key==='Enter') C.i++; });
document.getElementById('f').addEventListener('click',()=>C.f++);
</script>
"""


def run_control(cdp, R, tmpdir):
    p = os.path.join(tmpdir, 'ctl.html')
    io.open(p, 'w', encoding='utf-8').write(CONTROL_HTML)
    srv = Static(tmpdir)
    try:
        cdp.navigate(srv.url('ctl.html'))
        cdp.call('Page.setInterceptFileChooserDialog', {'enabled': True})
        cdp.key('Tab'); R.add('C-button', 'Tab → 버튼에 초점', cdp.active().startswith('button#b'), cdp.active())
        cdp.key('Enter'); R.add('C-button', 'Enter → click 1회', cdp.eval('C.b') == 1, 'clicks=%s' % cdp.eval('C.b'))
        cdp.key('Space'); R.add('C-button', 'Space → click 1회 더(총 2)', cdp.eval('C.b') == 2, 'clicks=%s' % cdp.eval('C.b'))
        cdp.key('Tab'); R.add('C-link', 'Tab → 링크에 초점', cdp.active().startswith('a#l'), cdp.active())
        cdp.key('Enter'); R.add('C-link', 'Enter → 링크 click 1회', cdp.eval('C.l') == 1, 'clicks=%s' % cdp.eval('C.l'))
        cdp.key('Space'); R.add('C-link', 'Space → 링크는 활성화되지 않는다(스크롤 키)', cdp.eval('C.l') == 1, 'clicks=%s' % cdp.eval('C.l'))
        cdp.key('Tab'); R.add('C-input', 'Tab → 입력창', cdp.active().startswith('input#i'), cdp.active())
        cdp.type_text('ab'); cdp.key('Space'); cdp.key('Enter')
        R.add('C-input', '타이핑+Space → 값 "ab " · Enter 는 keydown 만(버튼 click 없음)', cdp.eval("document.getElementById('i').value") == 'ab ' and cdp.eval('C.i') == 1 and cdp.eval('C.b') == 2,
              'value=%r enterKeydown=%s buttonClicks=%s' % (cdp.eval("document.getElementById('i').value"), cdp.eval('C.i'), cdp.eval('C.b')))
        cdp.key('Tab'); R.add('C-summary', 'Tab → summary', cdp.active().startswith('summary#s'), cdp.active())
        cdp.key('Enter'); o1 = cdp.eval("document.getElementById('d').open")
        cdp.key('Space'); o2 = cdp.eval("document.getElementById('d').open")
        R.add('C-summary', 'Enter → 열림 · Space → 닫힘', o1 is True and o2 is False, 'open after Enter=%s after Space=%s' % (o1, o2))
        cdp.key('Tab'); R.add('C-range', 'Tab → range', cdp.active().startswith('input#r'), cdp.active())
        cdp.key('ArrowRight'); cdp.key('ArrowRight')
        R.add('C-range', 'ArrowRight×2 → 값 2', cdp.eval("document.getElementById('r').value") == '2', 'value=%s' % cdp.eval("document.getElementById('r').value"))
        cdp.key('Tab'); R.add('C-file', 'Tab → 파일 입력', cdp.active().startswith('input#f'), cdp.active())
        cdp.drain('Page.fileChooserOpened')
        cdp.key('Enter')
        try:
            ev = cdp.wait_event('Page.fileChooserOpened', 5); opened = ev['params'].get('mode')
        except TimeoutError:
            opened = None
        R.add('C-file', 'Enter → 파일 선택창 열림(가로채기 이벤트) · 초점 유지', opened is not None and cdp.active().startswith('input#f'), 'mode=%s active=%s' % (opened, cdp.active()))
        cdp.key('Space')
        try:
            ev = cdp.wait_event('Page.fileChooserOpened', 5); opened2 = ev['params'].get('mode')
        except TimeoutError:
            opened2 = None
        R.add('C-file', 'Space → 파일 선택창 열림', opened2 is not None, 'mode=%s' % opened2)
    finally:
        srv.close()


FAKE_BACKUP = {'v': 1, 'port': {'d': '2026-09-01', 'a': {'418660': {'qty': '3', 'avg': '30000'}}, 'cash': 1000},
               'trades': [{'d': '2026-09-01', 'code': '418660', 'side': 'buy', 'qty': '3', 'px': '30000'}], 'goal': None}


def run_site(cdp, R, root, tmpdir):
    srv = Static(root)
    try:
        # ---- 신호 화면
        cdp.navigate(srv.url('signal.html'))
        for _ in range(50):
            if cdp.eval("typeof AUTO !== 'undefined' && !!AUTO && document.getElementById('verdict').textContent !== '—'"):
                break
            time.sleep(0.2)
        st0 = cdp.eval("JSON.stringify({auto:(typeof AUTO !== 'undefined' && !!AUTO), port:localStorage.getItem('b_port_v1'), trades:localStorage.getItem('b_trades_v1'), keys:Object.keys(localStorage)})")
        st0 = json.loads(st0)
        R.add('S0', '자동 판정 로드 · 격리 프로필(사용자 장부 키 b_port_v1·b_trades_v1 없음)', st0['auto'] and st0['port'] is None and st0['trades'] is None,
              'verdict=%s ls_keys=%s' % (cdp.eval("document.getElementById('verdict').textContent"), ','.join(st0['keys'])))
        # S1 접기 버튼 — 실제 Tab 으로 도달 → Enter/Space 활성화 횟수(리스너로 셈 · 합성 이벤트 없음)
        cdp.eval("window.__fc=0; document.querySelector('#portPanel .foldbtn').addEventListener('click',()=>window.__fc++); 1")
        n = cdp.tab_until("e.classList && e.classList.contains('foldbtn')", 20)
        R.add('S1-fold', 'Tab %d회 → 첫 접기 버튼' % n, n > 0, cdp.active())
        cdp.key('Enter'); f1 = cdp.eval("document.getElementById('portPanel').classList.contains('folded')"); c1 = cdp.eval('window.__fc')
        cdp.key('Space'); f2 = cdp.eval("document.getElementById('portPanel').classList.contains('folded')"); c2 = cdp.eval('window.__fc')
        R.add('S1-fold', 'Enter → 접힘(click 1) · Space → 펼침(click 2) · 초점 유지 · aria-expanded 갱신',
              f1 is True and c1 == 1 and f2 is False and c2 == 2 and cdp.active().startswith('button#foldbtn') and cdp.eval("document.activeElement.getAttribute('aria-expanded')") == 'true',
              'folded %s/%s clicks %s/%s active=%s expanded=%s' % (f1, f2, c1, c2, cdp.active(), cdp.eval("document.activeElement.getAttribute('aria-expanded')")))
        # S2 details(체결 기록 · 백업) — Enter 열기 · Space 닫기 · Enter 다시 열기
        n = cdp.tab_until("e.tagName==='SUMMARY' && e.textContent.includes('체결 기록')", 40)
        R.add('S2-details', 'Tab %d회 → 「체결 기록 · 백업」 summary' % n, n > 0, cdp.active())
        cdp.key('Enter'); o1 = cdp.eval("document.activeElement.parentElement.open")
        cdp.key('Space'); o2 = cdp.eval("document.activeElement.parentElement.open")
        cdp.key('Enter'); o3 = cdp.eval("document.activeElement.parentElement.open")
        R.add('S2-details', 'Enter 열림 · Space 닫힘 · Enter 열림', o1 is True and o2 is False and o3 is True, '%s/%s/%s' % (o1, o2, o3))
        # S5 백업 복원 확인창 — 파일은 자동화 API 로 주입(OS 선택창 아님) · 취소/확인 뒤 초점·다음 키
        fake = os.path.join(tmpdir, 'fake_backup.txt')
        io.open(fake, 'w', encoding='utf-8').write(json.dumps(FAKE_BACKUP))
        n = cdp.tab_until("e.id==='tlImpFile'", 30)
        R.add('S5-restore', 'Tab %d회 → 「파일에서 복원」 파일 입력(라벨 안)' % n, n > 0, cdp.active())
        qty_before = cdp.eval("(document.querySelector('#portPanel input[aria-label$=\"보유 수량\"]')||{}).value")
        oid = cdp.object_id("document.getElementById('tlImpFile')")
        cdp.drain('Page.javascriptDialogOpening')
        cdp.call('DOM.setFileInputFiles', {'files': [fake], 'objectId': oid})
        ev = cdp.wait_event('Page.javascriptDialogOpening', 10)
        R.add('S5-restore', '[주입] 확인창(confirm) 열림 · 문구', ev['params'].get('type') == 'confirm' and '덮어씁니다' in ev['params'].get('message', ''), ev['params'].get('message', '')[:60], kind='자동화 주입')
        cdp.call('Page.handleJavaScriptDialog', {'accept': False})
        time.sleep(0.3)
        a_cancel = cdp.active()
        cdp.key('Tab'); a_next = cdp.active()
        R.add('S5-restore', '취소 → 저장값 무변경 · 초점이 파일 입력에 남음 · 다음 Tab 이 CSV 내보내기 버튼',
              cdp.eval("localStorage.getItem('b_port_v1')") is None and a_cancel.startswith('input#tlImpFile') and a_next.startswith('button#tlExpCsv'),
              'ls=%s active=%s next=%s' % (cdp.eval("localStorage.getItem('b_port_v1')"), a_cancel, a_next), kind='자동화 주입')
        cdp.key('Tab', shift=True)
        R.add('S5-restore', 'Shift+Tab 으로 파일 입력 복귀', cdp.active().startswith('input#tlImpFile'), cdp.active())
        cdp.drain('Page.javascriptDialogOpening')
        cdp.call('DOM.setFileInputFiles', {'files': [fake], 'objectId': oid})
        cdp.wait_event('Page.javascriptDialogOpening', 10)
        cdp.call('Page.handleJavaScriptDialog', {'accept': True})
        time.sleep(0.5)
        a_ok = cdp.active()
        undo = cdp.eval("(()=>{const d=document.getElementById('undoBar'); return d? d.getAttribute('role')+'|'+d.textContent.slice(0,12) : null})()")
        qty = cdp.eval("(document.querySelector('#portPanel input[aria-label$=\"보유 수량\"]')||{}).value")
        cdp.key('Tab'); a_next2 = cdp.active()
        R.add('S5-restore', '확인 → 수량 3 복원 · undoBar role=status · 초점 유지 · 다음 Tab 정상',
              qty == '3' and undo and undo.startswith('status|') and a_ok.startswith('input#tlImpFile') and a_next2.startswith('button#tlExpCsv'),
              'qty %s→%s undo=%s active=%s next=%s' % (qty_before, qty, undo, a_ok, a_next2), kind='자동화 주입')
        # 되돌리기 버튼에 키보드로 도달 → Enter → 복원 전으로
        n = cdp.tab_until("e.id==='undoBtn'", 30)
        if n < 0:
            n = cdp.tab_until("e.id==='undoBtn'", 60)
        if n > 0:
            cdp.key('Enter'); time.sleep(0.3)
            act = cdp.active()
            # 되돌리기 버튼은 자기 자신(undoBar)을 지운다 — 초점이 body 로 떨어지면 다음 키가 갈 곳이 없다(v232 에서 파일 입력으로 복귀시킴)
            R.add('S5-restore', 'Tab → 되돌리기 버튼 · Enter → 수량 빈 값으로 복귀 · 초점이 body 가 아니라 복원 컨트롤에 남음',
                  cdp.eval("(document.querySelector('#portPanel input[aria-label$=\"보유 수량\"]')||{}).value") == '' and not act.startswith('body'),
                  'qty=%r active=%s' % (cdp.eval("(document.querySelector('#portPanel input[aria-label$=\"보유 수량\"]')||{}).value"), act))
            cdp.key('Tab'); R.add('S5-restore', '되돌리기 뒤 다음 Tab 이 예측 가능한 컨트롤(CSV 내보내기)로', cdp.active().startswith('button#tlExpCsv'), cdp.active())
        else:
            R.add('S5-restore', 'Tab 으로 되돌리기 버튼 도달', False, cdp.active())
        # S6 파일 입력 키보드 접근 — Enter/Space 가 선택창을 여는가(가로채기 · OS 창은 안 뜸) · 기존 입력 보존
        cdp.call('Page.setInterceptFileChooserDialog', {'enabled': True})
        cdp.eval("document.querySelector('#portPanel input[aria-label$=\"평단가(선택)\"]').value='31000'; document.querySelector('#portPanel input[aria-label$=\"평단가(선택)\"]').dispatchEvent(new Event('input',{bubbles:true})); 1")
        n = cdp.tab_until("e.id==='tlImpFile'", 60)
        if n < 0:
            cdp.eval("document.getElementById('tlImpFile').focus(); 1")   # setup — 실제 Tab 도달은 위 S5 에서 확인
        cdp.drain('Page.fileChooserOpened')
        cdp.key('Enter')
        try:
            m1 = cdp.wait_event('Page.fileChooserOpened', 5)['params'].get('mode')
        except TimeoutError:
            m1 = None
        cdp.key('Space')
        try:
            m2 = cdp.wait_event('Page.fileChooserOpened', 5)['params'].get('mode')
        except TimeoutError:
            m2 = None
        avg = cdp.eval("document.querySelector('#portPanel input[aria-label$=\"평단가(선택)\"]').value")
        R.add('S6-file', 'Enter/Space → 파일 선택창 열림 이벤트 · 초점 유지 · 기존 입력(평단가 31000) 보존 · 선택 없음=취소',
              m1 is not None and m2 is not None and cdp.active().startswith('input#tlImpFile') and avg == '31000', 'enter=%s space=%s active=%s avg=%s' % (m1, m2, cdp.active(), avg))
        cdp.call('Page.setInterceptFileChooserDialog', {'enabled': False})
        # S3 타임머신 — summary Enter → 칩 Enter → 재생 Space → 슬라이더 화살표
        n = cdp.tab_until("e.tagName==='SUMMARY' && e.textContent.includes('타임머신')", 80)
        R.add('S3-tm', 'Tab %d회 → 타임머신 summary' % n, n > 0, cdp.active())
        cdp.key('Enter')
        R.add('S3-tm', 'Enter → 열림', cdp.eval("document.getElementById('tmFold').open") is True, cdp.active())
        cdp.eval("window.__cc=0; document.querySelectorAll('#tmTabs .chip')[1].addEventListener('click',()=>window.__cc++); 1")
        n = cdp.tab_until("e.classList && e.classList.contains('chip') && e.textContent.startsWith('GFC')", 6)
        cdp.key('Enter')
        pressed = cdp.eval("[...document.querySelectorAll('#tmTabs .chip')].map(x=>x.getAttribute('aria-pressed')).join(',')")
        R.add('S3-tm', 'Tab → GFC 칩 · Enter → aria-pressed 갱신(false,true,false,false) · click 1 · 초점 유지', n > 0 and pressed == 'false,true,false,false' and cdp.eval('window.__cc') == 1 and cdp.active().startswith('button#chip'), 'pressed=%s clicks=%s active=%s' % (pressed, cdp.eval('window.__cc'), cdp.active()))
        n = cdp.tab_until("e.id==='tmPlay'", 6)
        cdp.key('Space'); time.sleep(0.35); t1 = cdp.eval("document.getElementById('tmPlay').textContent"); v1 = cdp.eval("+document.getElementById('tmSlider').value")
        cdp.key('Space'); time.sleep(0.15); t2 = cdp.eval("document.getElementById('tmPlay').textContent"); v2 = cdp.eval("+document.getElementById('tmSlider').value"); time.sleep(0.3); v3 = cdp.eval("+document.getElementById('tmSlider').value")
        R.add('S3-tm', 'Tab → 재생 · Space → 「⏸ 정지」·진행 · Space → 「▶ 재생」·멈춤', n > 0 and '정지' in t1 and v1 >= 1 and '재생' in t2 and v3 == v2, 't1=%s v1=%s t2=%s v2=%s v3=%s' % (t1, v1, t2, v2, v3))
        n = cdp.tab_until("e.id==='tmSlider'", 4)
        v0 = cdp.eval("+document.getElementById('tmSlider').value")
        cdp.key('ArrowRight'); cdp.key('ArrowRight')
        R.add('S3-tm', 'Tab → 슬라이더 · ArrowRight×2 → +2 · 날짜 문구 갱신', n > 0 and cdp.eval("+document.getElementById('tmSlider').value") == v0 + 2 and ('%d거래일' % (v0 + 2)) in cdp.eval("document.getElementById('tmDay').textContent"), 'v %s→%s day=%s' % (v0, cdp.eval("+document.getElementById('tmSlider').value"), cdp.eval("document.getElementById('tmDay').textContent")[:30]))
        # ---- 노트 화면
        cdp.navigate(srv.url('notes.html'))
        cdp.eval("window.__nc=0; document.querySelector('#filters [data-f=fix]').addEventListener('click',()=>window.__nc++); 1")
        n = cdp.tab_until("e.getAttribute && e.getAttribute('data-f')==='fix'", 12)
        cdp.key('Enter')
        st = cdp.eval("[...document.querySelectorAll('#filters button')].map(x=>x.getAttribute('data-f')+':'+x.getAttribute('aria-pressed')+':'+x.classList.contains('on')).join(' ')")
        hid = cdp.eval("[...document.querySelectorAll('.item')].filter(i=>i.hidden).length")
        R.add('N1-filter', 'Tab %d회 → 「고친 것」 · Enter → click 1 · aria-pressed/.on 갱신 · 항목 숨김 · 초점 유지' % n, n > 0 and cdp.eval('window.__nc') == 1 and 'fix:true:true' in st and 'all:false:false' in st and hid > 0 and cdp.active().startswith('button#on'), 'clicks=%s %s hidden=%s active=%s' % (cdp.eval('window.__nc'), st, hid, cdp.active()))
        cdp.key('Tab'); cdp.key('Space')
        st2 = cdp.eval("[...document.querySelectorAll('#filters button')].map(x=>x.getAttribute('data-f')+':'+x.getAttribute('aria-pressed')).join(' ')")
        R.add('N1-filter', 'Tab → 「없앤 것」 · Space → 눌림 이동(del:true · fix:false) · 초점 유지', 'del:true' in st2 and 'fix:false' in st2 and cdp.active().startswith('button#on'), '%s active=%s' % (st2, cdp.active()))
        n = cdp.tab_until("e.classList && e.classList.contains('foldbtn')", 6)
        sec = cdp.eval("document.activeElement.closest('[data-fold]').id")
        cdp.key('Enter'); f1 = cdp.eval("document.getElementById('%s').classList.contains('folded')" % sec); e1 = cdp.eval("document.activeElement.getAttribute('aria-expanded')")
        cdp.key('Enter'); f2 = cdp.eval("document.getElementById('%s').classList.contains('folded')" % sec)
        R.add('N2-fold', 'Tab → 첫 접기 버튼 · Enter → 접힘(aria-expanded false) · Enter → 펼침', n > 0 and f1 is True and e1 == 'false' and f2 is False, 'sec=%s folded %s/%s expanded=%s' % (sec, f1, f2, e1))
        # ---- 설명서 검색 — 타이핑 후 결과 문구(aria-live) · 초점
        cdp.navigate(srv.url('guide.html'))
        n = cdp.tab_until("e.id==='gsearch'", 12)
        cdp.type_text('재조정')
        time.sleep(0.3)
        msg = cdp.eval("document.getElementById('gsearchMsg').textContent")
        R.add('G1-search', 'Tab %d회 → 검색창 · 타이핑 → 결과 문구(aria-live 영역) · 초점 유지' % n, n > 0 and '재조정' in msg and '찾음' in msg and cdp.active().startswith('input#gsearch'), 'msg=%s active=%s' % (msg, cdp.active()))
    finally:
        srv.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--control', action='store_true')
    ap.add_argument('--site', action='store_true')
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--browser', default=None)
    ap.add_argument('--headed', action='store_true')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    if not (a.control or a.site):
        a.control = a.site = True
    exe = find_browser(a.browser)
    tmp = tempfile.mkdtemp(prefix='kbchk_')
    br = Browser(exe, headed=a.headed)
    R = Report()
    print('브라우저 %s · %s · 임시 프로필 %s' % (exe, br.version, br.profile))
    try:
        cdp = br.page()
        if a.control:
            print('\n[대조 페이지 — 하네스 검증]')
            run_control(cdp, R, tmp)
            if R.fails():
                print('\n대조 페이지 실패 — 사이트 판정을 내리지 않는다')
                sys.exit(2)
        if a.site:
            print('\n[사이트 — 빠진 경로]')
            cdp = br.page()
            run_site(cdp, R, os.path.abspath(a.root), tmp)
    finally:
        br.close()
        shutil.rmtree(tmp, ignore_errors=True)
    if a.out:
        io.open(a.out, 'w', encoding='utf-8').write(json.dumps(R.rows, ensure_ascii=False, indent=1))
    bad = R.fails()
    print('\n합계 %d · 불일치 %d' % (len(R.rows), len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
