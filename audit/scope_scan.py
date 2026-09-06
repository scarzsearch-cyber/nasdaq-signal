# -*- coding: utf-8 -*-
"""읽기 전용 범위 스캔 (2026-09-06 · 감사 재현 도구 · CI 미등재) — research/*.py · research/*.md · research_kit.py ·
내가_보는_것/*.py 의 import 그래프 · 피호출(imported_by) · 종류별 참조(워크플로·verify_all·deploy·audit·화면·문서) ·
data 산출물 · 기존 검사 현황(COVERAGE_MAP 의 수준·담당)을 표로 뽑는다. **계산 실행·수정 없음.**

장부: audit/RESEARCH_SCOPE_2026-09-06.md(A/B/C/D 분류) · audit/UNCLEAR34_2026-09-06.md(34개 행의 호출자·출력·인용처)가 이 스캔에서 나왔다.
실행: python audit/scope_scan.py [--root <저장소>] [--out <json 경로>]
  --out 을 주면 행 전체를 JSON 으로 저장한다(생성물 — 커밋하지 않는다). 없으면 요약만 출력.
한계: import 는 정적 정규식(`import x` / `from x import`) · 참조는 파일명(stem) 언급이라 실행 호출과 주석 언급을 사람이 가른다 ·
  「산출물」은 data/*.json·csv 쓰기 패턴만 센다(원자료 data/hist/* 읽기 제외).
  git 의 한글 경로 이스케이프를 `core.quotepath=false` 로 끈다(원판은 이 때문에 `점검.py` 를 손으로 넣었다).
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)
COVERAGE = 'audit/COVERAGE_MAP_2026-09-06.md'


def read(p):
    try:
        return io.open(p, encoding='utf-8', errors='ignore').read()
    except Exception:
        return ''


def scan(root):
    os.chdir(root)
    ls = subprocess.run(['git', '-c', 'core.quotepath=false', 'ls-files'], capture_output=True, text=True, encoding='utf-8').stdout
    tracked = [t for t in ls.split('\n') if t]
    py = [t for t in tracked if t.endswith('.py')]
    targets = [t for t in tracked if (t.startswith('research/') and t.endswith(('.py', '.md')))
               or t == 'research_kit.py' or (t.startswith('내가_보는_것/') and t.endswith('.py'))]
    texts = {p: read(p) for p in tracked if p.endswith(('.py', '.md', '.yml', '.html', '.json', '.txt'))}

    # 1) 검사 현황표 행(수준·담당·근거)
    cov = {}
    for line in read(COVERAGE).split('\n'):
        m = re.match(r'\| (.+?) \| `(.+?)` \| (.+?) \| (.+?) \| (.+?) \| (.*?) \| (.*?) \| (.*?) \|$', line)
        if m:
            cov[m.group(2)] = dict(grp=m.group(1), kind=m.group(3), owner=m.group(4), level=m.group(5),
                                   best=m.group(6), other=m.group(7), changed=m.group(8))

    # 2) import 그래프(저장소 모듈만)
    mods = {}
    for p in py:
        name = p[:-3].replace('/', '.').replace('\\', '.')
        mods[name] = p
        if p.startswith('research/'):
            mods[os.path.basename(p)[:-3]] = p          # research 안에서 sys.path 로 직접 import
        if '/' not in p:
            mods[p[:-3]] = p
    imports, rev = defaultdict(set), defaultdict(set)
    IMP = re.compile(r'^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+(?:\s*,\s*[\w\.]+)*))', re.M)
    for p in py:
        for m in IMP.finditer(texts.get(p, '')):
            names = [m.group(1)] if m.group(1) else [x.strip() for x in m.group(2).split(',')]
            for n in names:
                for cand in (n, n.split('.')[0], 'research.' + n):
                    if cand in mods and mods[cand] != p:
                        imports[p].add(mods[cand])
                        rev[mods[cand]].add(p)

    # 3) 종류별 참조(파일명 언급)
    kinds = {'workflow': [t for t in tracked if t.startswith('.github/')],
             'verify_all': ['verify_all.py'],
             'deploy': [t for t in tracked if t.startswith('deploy/') and t.endswith('.py')],
             'owner_tools': [t for t in tracked if t.startswith('내가_보는_것/')],
             'audit_py': [t for t in tracked if t.startswith('audit/') and t.endswith('.py')],
             'kit': ['research_kit.py'], 'screens': ['signal.html', 'guide.html', 'notes.html'],
             'strategy_docs': ['01_Strategy_Logic.md', '02_Risk_Management.md', '03_System_Params.md', '04_Rejected_Research.md'],
             'meta_docs': ['CLAUDE.md', 'FILES.md', 'HANDOFF.md', 'README.md'] + [t for t in tracked if t.startswith('research/') and t.endswith('.md')],
             'research_py': [t for t in tracked if t.startswith('research/') and t.endswith('.py')]}

    def refs_of(target):
        stem = os.path.splitext(os.path.basename(target))[0]
        pat = re.compile(r'(?<![\w-])' + re.escape(stem) + r'(?:\.py)?(?![\w])')
        out = {}
        for k, files in kinds.items():
            hits = [f for f in files if f != target and pat.search(texts.get(f, ''))]
            if hits:
                out[k] = hits
        return out

    # 4) data 산출물 쓰기 패턴 + 그 파일의 소비자
    WRITE = re.compile(r"(?:open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]w|to_csv\(\s*['\"]([^'\"]+)['\"]|json\.dump\([^)]*open\(\s*['\"]([^'\"]+)['\"]"
                       r"|_write\w*\(\s*['\"]([^'\"]+)['\"]|OUT\s*=\s*['\"]([^'\"]+)['\"]|['\"](data/[A-Za-z0-9_./-]+\.(?:json|csv))['\"])")

    def outputs_of(p):
        outs = set()
        for m in WRITE.finditer(texts.get(p, '')):
            v = next((g for g in m.groups() if g), None)
            if v and (v.startswith('data/') or v.endswith(('.json', '.csv'))):
                outs.add(v)
        return sorted(outs)

    def consumers(path):
        base = os.path.basename(path)
        return sorted(f for f in tracked if f.endswith(('.py', '.html', '.yml')) and f != path and base in texts.get(f, ''))

    rows = []
    for t in targets:
        c = cov.get(t, {})
        rows.append(dict(path=t, level=c.get('level', '?'), owner=c.get('owner', '?'), best=c.get('best', ''), other=c.get('other', ''),
                         imports=sorted(imports.get(t, [])), imported_by=sorted(rev.get(t, [])), refs=refs_of(t),
                         outputs=[(o, consumers(o)) for o in outputs_of(t)] if t.endswith('.py') else []))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--out', default=None, help='행 전체 JSON 저장 경로(생성물 · 커밋 금지)')
    a = ap.parse_args()
    rows = scan(os.path.abspath(a.root))
    if a.out:
        with io.open(a.out, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    print('files', len(rows))
    for r in rows:
        if not r['path'].endswith('.py'):
            continue
        rk = {k: len(v) for k, v in r['refs'].items()}
        print('%-46s %-24s imp_by=%-2d refs=%s outs=%s' % (r['path'], r['level'][:22], len(r['imported_by']), rk, [o for o, _ in r['outputs']]))


if __name__ == '__main__':
    main()
