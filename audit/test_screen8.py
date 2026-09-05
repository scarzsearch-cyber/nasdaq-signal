# -*- coding: utf-8 -*-
"""화면 갱신 순서·저장/복원 경계·배포본 CSP 회귀 (2026-09-06 · v229 · 장부 audit/SCREEN_DYNAMICS_2026-09-06.md · audit/CSP_2026-09-06.md).

signal.html 의 실제 함수 본문을 꺼내 node 로 돈다(test_ops_review2 의 방식). 브라우저 실측은 장부에 있고 여기서는
그 결함이 다시 생기면 실패하도록 고정한다:
  D1 loadPrice — 느린 옛 응답이 새 스냅샷을 덮어쓰지 않는다 · 서버가 더 옛 값을 줘도 뒤로 안 간다 · 뒤늦은 실패가 성공을 안 지운다
  D2 sanitizeBackup — 버린 체결 수를 dropped 로 알린다(살균 자체는 v186 그대로)
  D3 loadPort/loadTrades — 손상된 저장값은 <키>_bad 로 격리하고 기본값으로 부팅 · 정상값은 그대로
  D4 applyBackup — 되돌리기 스냅샷 저장(lsSet) 실패면 덮어쓰지 않는다
  C1 csp_inject — 세 화면 소스에 인라인 핸들러·외부 스크립트가 없고 스크립트 수만큼 해시가 나온다(배포 스텝과 같은 함수)
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'deploy'))
SRC = io.open(os.path.join(ROOT, 'signal.html'), encoding='utf-8').read()


def extract(start, end):
    i = SRC.index(start)
    j = SRC.index(end, i)
    return SRC[i:j]


def node_available():
    return shutil.which('node') is not None


def run_node(js):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, 't.js')
        with io.open(p, 'w', encoding='utf-8') as f:
            f.write(js)
        r = subprocess.run(['node', p], capture_output=True, text=True, encoding='utf-8', timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


PRELUDE = r"""
const window = globalThis; const document = {getElementById(){return null}, querySelectorAll(){return []}};
let warned = []; window.__sysWarn = (m) => warned.push(String(m));
const store = new Map(); let failKeys = new Set();
const localStorage = {getItem:(k)=>store.has(k)?store.get(k):null, setItem:(k,v)=>{ if(failKeys.has(k)) throw new Error('QuotaExceededError'); store.set(k,String(v)); }, removeItem:(k)=>store.delete(k)};
let LS_WARNED = false;
"""


class D1_PriceRefreshOrdering(unittest.TestCase):
    def test_late_old_response_does_not_overwrite(self):
        if not node_available():
            self.skipTest('node 없음')
        fn = extract('let _priceSeq = 0;', '\n/* 스냅샷이 몇 분 전 것인지')
        js = PRELUDE + r"""
let PRICE = null; const q = []; const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function getJSON(p){ const h = q.shift(); return h(); }
const mk = (iso, px) => ({as_of_iso: iso, items: {'418660': {px}}});
""" + fn + r"""
(async () => {
  const out = {};
  // 옛 응답이 느리게, 새 응답이 빨리 — 새 값이 남아야 한다
  q.push(() => sleep(60).then(() => mk('2026-09-05T10:05:20+09:00', 38000)));
  q.push(() => mk('2026-09-05T10:10:20+09:00', 38900));
  const a = loadPrice(); await sleep(5); const b = loadPrice(); await Promise.all([a, b]);
  out.afterRace = PRICE.as_of_iso;
  // 서버가 더 옛 스냅샷을 돌려줘도 뒤로 가지 않는다
  q.push(() => mk('2026-09-05T10:05:20+09:00', 38000)); await loadPrice(); out.afterOlder = PRICE.as_of_iso;
  // 뒤늦은 실패가 새 성공을 지우지 않는다
  q.push(() => sleep(60).then(() => { throw new TypeError('offline'); }));
  q.push(() => mk('2026-09-05T10:15:20+09:00', 39000));
  const c = loadPrice(); await sleep(5); const d = loadPrice(); await Promise.all([c, d]);
  out.afterLateFail = PRICE.as_of_iso;
  // 최신 요청 자체가 실패하면 null(옛 값을 새 값인 척 안 한다 — v202 규약 유지)
  q.push(() => { throw new TypeError('offline'); }); await loadPrice(); out.afterFail = PRICE;
  console.log(JSON.stringify(out));
})();
"""
        out = run_node(js)
        self.assertEqual(out['afterRace'], '2026-09-05T10:10:20+09:00')
        self.assertEqual(out['afterOlder'], '2026-09-05T10:10:20+09:00')
        self.assertEqual(out['afterLateFail'], '2026-09-05T10:15:20+09:00')
        self.assertIsNone(out['afterFail'])


class D2_D3_D4_StorageBoundary(unittest.TestCase):
    def _js(self):
        parts = [
            extract('function lsSet(k, v){', '\n/* [v229] 저장값 모양 검증'),
            extract('const OK_CODE = /^\\d{6}$/;', '\n/* [v186] 링크 백업'),
            extract('const QUAR = [];', '\nfunction load(){'),
            extract('function loadPort(){', '\nfunction savePort(){'),
            extract('function loadTrades(){', '\nfunction saveTrades(){'),
            extract('function applyBackup(j, from){', '\n/* [v186] ★ 백업 내용 살균'),
        ]
        return '\n'.join(parts)

    def test_storage_boundary(self):
        if not node_available():
            self.skipTest('node 없음')
        js = PRELUDE + r"""
const PKEY = 'b_port_v1', TKEY = 'b_trades_v1', GKEY = 'b_goal_v1', UNDOKEY = 'b_undo_v1';
let PORT = {d:null, a:{}, cash:0}, TRADES = [], GOAL = {target: 0};
const kstISO = () => '2026-09-06'; let applied = 0, chips = 0; let confirms = [], alerts = [];
function applyState(j){ applied++; PORT = j.port; TRADES = j.trades; }
function showUndoChip(){ chips++; }
function confirm(m){ confirms.push(m); return true; } function alert(m){ alerts.push(String(m)); }
""" + self._js() + r"""
const out = {};
// D2 dropped
const s = sanitizeBackup({v:1, port:{a:{}}, trades:[{d:'2026-09-01',code:'418660',side:'buy',qty:1,px:1},{d:'bad',code:'418660',side:'buy'},{d:'2026-09-01',code:'000000',side:'x'}]});
out.kept = s.trades.length; out.dropped = s.dropped; out.droppedNotSerialized = !('dropped' in JSON.parse(JSON.stringify(s)));
// D3 garbage → quarantine + defaults ; valid → kept
store.set(PKEY, '[]'); store.set(TKEY, '{}'); loadPort(); loadTrades();
out.g1 = {port: JSON.stringify(PORT), trades: TRADES.length, badPort: store.get(PKEY+'_bad'), badTrades: store.get(TKEY+'_bad'), live: store.has(PKEY), warned: warned.length};
store.clear(); warned = [];
store.set(TKEY, JSON.stringify([null, 1, {d:'x'}, {d:'2026-09-01',code:'418660',side:'buy',qty:'3',px:'1'}])); loadTrades();
out.g2 = {trades: TRADES.length, rewritten: JSON.parse(store.get(TKEY)).length, bad: !!store.get(TKEY+'_bad'), warned: warned.length};
store.clear(); warned = [];
store.set(PKEY, JSON.stringify({d:'2026-09-01', a:{'418660':{qty:'3', avg:'38000'}}, cash: 0})); loadPort();
out.valid = {qty: PORT.a['418660'].qty, avg: PORT.a['418660'].avg, bad: store.has(PKEY+'_bad'), warned: warned.length};
// D4 undo save failure → abort, nothing applied
failKeys = new Set([UNDOKEY]);
const bk = {v:1, port:{d:'2026-09-02', a:{'418660':{qty:'99'}}, cash:5}, trades:[{d:'2026-09-02',code:'418660',side:'buy',qty:99,px:1},{d:'bad',code:'418660',side:'buy'}]};
const r1 = applyBackup(bk, '파일');
out.undoFail = {returned: r1, applied, chips, alert: alerts.length, confirmMentionsDrop: confirms[0].indexOf('1건은 제외') >= 0, qty: PORT.a['418660'].qty};
failKeys = new Set();
const r2 = applyBackup(bk, '파일');
out.normal = {returned: r2, applied, chips, undoStored: store.has(UNDOKEY), qty: PORT.a['418660'].qty};
console.log(JSON.stringify(out));
"""
        out = run_node(js)
        self.assertEqual((out['kept'], out['dropped']), (1, 2))
        self.assertTrue(out['droppedNotSerialized'], 'dropped 는 백업 파일에 섞이지 않는 비열거 속성')
        g1 = out['g1']
        self.assertEqual(g1['port'], json.dumps({'d': None, 'a': {}, 'cash': 0}, separators=(',', ':')))
        self.assertEqual(g1['trades'], 0)
        self.assertEqual((g1['badPort'], g1['badTrades']), ('[]', '{}'))
        self.assertFalse(g1['live'], '손상값은 격리 뒤 원래 키에서 지운다')
        self.assertGreaterEqual(g1['warned'], 1)
        self.assertEqual((out['g2']['trades'], out['g2']['rewritten']), (1, 1))
        self.assertTrue(out['g2']['bad'])
        self.assertEqual((out['valid']['qty'], out['valid']['avg'], out['valid']['bad'], out['valid']['warned']), ('3', '38000', False, 0))
        u = out['undoFail']
        self.assertEqual((u['returned'], u['applied'], u['chips'], u['alert'], u['qty']), (False, 0, 0, 1, '3'))
        self.assertTrue(u['confirmMentionsDrop'])
        n = out['normal']
        self.assertEqual((n['returned'], n['applied'], n['chips'], n['undoStored'], n['qty']), (True, 1, 1, True, '99'))


class C1_CspInjectOnRealScreens(unittest.TestCase):
    def test_real_screens_accept_hash_policy(self):
        import csp_inject as C
        for name in ('signal.html', 'guide.html', 'notes.html'):
            html = io.open(os.path.join(ROOT, name), encoding='utf-8').read()
            C.check_handlers(html)                                  # 인라인 핸들러 0 (있으면 ValueError)
            out, hashes = C.inject(html)
            n_scripts = len([m for m in C.SCRIPT_RE.finditer(html)])
            self.assertEqual(len(hashes), n_scripts, name)
            self.assertEqual(out.count('Content-Security-Policy'), 1, name)
            self.assertIn("connect-src 'self'", out)
            self.assertNotIn("'unsafe-inline'; font", out)         # script 쪽엔 unsafe-inline 없음
            self.assertIn("style-src 'self' 'unsafe-inline'", out)

    def test_selftest(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'deploy', 'csp_inject.py'), '--selftest'],
                           capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])

    def test_pages_runs_injector_after_stamp(self):
        y = io.open(os.path.join(ROOT, '.github', 'workflows', 'pages.yml'), encoding='utf-8').read()
        self.assertLess(y.index('deploy/stamp_rev.py _site/index.html'), y.index('deploy/csp_inject.py _site/index.html'),
                        'CSP 해시는 도장 치환 뒤에 계산해야 한다')
        self.assertIn('|| echo "::warning::CSP', y, '주입 실패는 fail-open(CSP 없는 배포본)')
        # 주입 뒤에는 세 화면을 다시 만지는 스텝이 없다(해시가 최종 배포본과 어긋날 자리 없음) — 주입 줄 뒤 upload 전까지 data/ 복사·rm 뿐
        tail = y[y.index('deploy/csp_inject.py _site/index.html'):y.index('upload-pages-artifact')]
        for bad in ('index.html', 'guide.html', 'notes.html'):
            self.assertNotIn(bad, tail.split('\n', 1)[1], '주입 뒤 %s 를 다시 만지는 스텝이 생겼다' % bad)

    def test_step_is_fail_open_with_warning(self):
        """주입기가 죽어도 스텝은 성공(rc 0)하고 ::warning:: 주석이 남는다 — pages.yml 의 실제 줄을 bash 로 흉내낸다."""
        bash = shutil.which('bash') or next((p for p in (r'C:\Program Files\Git\bin\bash.exe',) if os.path.exists(p)), None)
        if not bash:
            self.skipTest('bash 없음')
        y = io.open(os.path.join(ROOT, '.github', 'workflows', 'pages.yml'), encoding='utf-8').read()
        line = next(l for l in y.splitlines() if 'deploy/csp_inject.py _site/index.html' in l and not l.strip().startswith('#')).strip()
        sim = line.replace('python3 deploy/csp_inject.py _site/index.html _site/guide.html _site/notes.html', 'false')
        r = subprocess.run([bash, '-c', sim], capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('::warning::CSP', r.stdout)

    def test_written_policy_matches_final_html(self):
        """실제 세 화면 사본에 주입한 뒤 다시 읽어, meta 의 해시 = 문서의 실제 스크립트 해시. 도장(stamp_rev) 뒤 계산이므로 index 는 도장을 먼저 찍는다."""
        import csp_inject as C
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for name in ('signal.html', 'guide.html', 'notes.html'):
                p = os.path.join(td, 'index.html' if name == 'signal.html' else name)
                shutil.copy(os.path.join(ROOT, name), p)
                paths.append(p)
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'deploy', 'stamp_rev.py'), paths[0], 'v999 · 2026-09-06 00:00'],
                               capture_output=True, text=True, encoding='utf-8', timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr[-400:])
            self.assertEqual(C.run_files(paths), 0)
            for p in paths:
                back = io.open(p, encoding='utf-8').read()
                self.assertEqual(C.script_hashes(back), C.meta_hashes(back), p)
                self.assertEqual(back.count('Content-Security-Policy'), 1)
            stamped = io.open(paths[0], encoding='utf-8').read()
            self.assertIn('const HTML_REV = "v999', stamped, '도장이 해시 계산 전에 찍혀 있어야 한다')


if __name__ == '__main__':
    unittest.main()
