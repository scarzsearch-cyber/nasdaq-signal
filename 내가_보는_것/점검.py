# -*- coding: utf-8 -*-
"""
점검 — 전략이 서 있는 땅이 아직 멀쩡한가.

**[v140] 이제 이걸 직접 돌릴 의무는 없다.** GitHub Actions 의 「자동 파수꾼」이
매주 대신 돌리고, 결과를 화면(오늘의 신호 → 버전·동결)에 한 줄로 띄운다.
이상이 생겼을 때만 카톡이 온다. 이 파일은 **직접 확인하고 싶을 때만** 쓴다.

    python 내가_보는_것/점검.py          ← 사람이 읽는 출력
    python 내가_보는_것/점검.py --json   ← 자동화가 읽는 출력 (파수꾼이 쓴다)

어느 폴더에서 실행해도 된다 — 아래 chdir 이 저장소 루트를 스스로 찾는다.

무엇을 보는가:
  [1] 전제 감시  — 전략이 아직 유효한 조건 안에 있나 (research/surv_map.py)
                   느린 변수 4종의 분포 위치 + 4다리 상품 생존(AUM)
  [2] 체결 비용  — 0.2% 가정이 실측과 맞나 (research/exec_cost.py)

자세한 설명: 같은 폴더의 운영_점검표.md
"""
import json
import os
import re
import subprocess
import sys

# 이 파일은 내가_보는_것/ 안에 있으므로 **저장소 루트는 부모 폴더**다.
# research/ · data/ 를 찾으려면 루트로 내려가야 한다 (어느 위치에서 실행하든 동작).
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LINE = '=' * 62
THIN = '-' * 62

# 상장폐지 경보가 떴을 때 **그 순간 보여줄** 대체 상품. 문서에 적으면 안 읽힌다
# (웹사이트 자족 원칙) — 경보 문구 안에 같이 실어 화면·카톡에 그대로 뜨게 한다.
# 2026-08-31 네이버 ETF 전체 목록(1,163종목) 대조로 실재 확인. 시총은 그날 조회값.
SUBSTITUTE = {
    '418660': '409820 KODEX 미국나스닥100레버리지(합성 H) 2,550억 — '
              '★단 환헤지라 성격이 다르다(현행은 환노출). 원화 성과가 달라진다',
    '458730': '446720 SOL / 402970 ACE / 489250 KODEX 미국배당다우존스 (각 6,000~10,000억) — 같은 지수',
    '305080': '308620 KODEX 미국10년국채선물 938억 — 동성격은 이것 하나뿐'
              '(나머지 미국채 ETF 는 30년(H)·혼합형이라 다른 물건)',
    '411060': '0072R0 TIGER KRX금현물 12,157억 — 같은 기초자산',
}

JSON_MODE = '--json' in sys.argv[1:]


def say(*a):
    """사람이 읽는 줄. --json 일 때는 아무것도 찍지 않는다(출력이 JSON 하나여야 하므로)."""
    if not JSON_MODE:
        print(*a)


def run(script):
    """하위 스크립트를 돌리고 (성공여부, 출력) 을 준다."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    try:
        p = subprocess.run([sys.executable, script], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           env=env, timeout=900)
        return p.returncode == 0, (p.stdout or '') + (p.stderr or '')
    except Exception as e:
        return False, f'실행 실패: {e}'


def pick(out, *keys):
    """출력에서 키워드가 들어간 줄만 뽑는다."""
    got = []
    for ln in out.splitlines():
        if any(k in ln for k in keys):
            got.append(ln.rstrip())
    return got


def main():
    from datetime import date
    todo = []
    # 자동화(파수꾼)와 화면이 읽는 결과. 사람이 읽는 출력과 **같은 계산에서 나온다** —
    # 두 벌로 만들지 않는다(수치가 갈리는 사고를 여기서 원천 차단).
    R = {'as_of': str(date.today()), 'level': 0, 'level_msg': '', 'todo': [],
         'vars': [], 'aum': [], 'exec': {}, 'ok': True}

    say(f'\n{LINE}\n 점검 — {date.today()}\n{LINE}')

    # ---- [1] 전제 감시 -----------------------------------------------------
    say('\n[1/2] 전제 감시 — 전략이 아직 유효한 조건 안에 있나')
    ok1, out1 = run(os.path.join('research', 'surv_map.py'))
    if not ok1:
        say('  ★ 실행 실패 — 아래 원문을 확인하라')
        say('  ' + out1.strip().splitlines()[-1] if out1.strip() else '')
        todo.append('전제 감시 스크립트가 실패했다 — AI에게 원문을 보여줄 것')
        R['ok'] = False
        R['level'] = -1
        R['level_msg'] = '점검 실패 — 계산이 돌지 않았다'
    else:
        # SURVIVAL_MONITOR §F 의 감시 밴드 — 실측 분위에서 나온 값(임의 임계 아님).
        #   (이름, 주의선, 역사범위밖선, 방향)  방향 'lo'=작아지면 나쁨, 'hi'=커지면 나쁨
        BANDS = [('지수 10년 CAGR', 4.1, -8.1, 'lo'),
                 ('지수 20년 CAGR', 9.5, 3.1, 'lo'),
                 ('지수 3년 변동성', 35.6, 51.9, 'hi'),
                 ('2배 드래그 3년', 11.7, 29.4, 'hi')]
        cur = {}
        for ln in out1.splitlines():
            m = re.match(r'\s{2}(\S.*?)\s{2,}([+-]?[\d.]+)%', ln)
            if m:
                cur.setdefault(m.group(1).strip(), float(m.group(2)))
        warn, out_of_range = [], []
        say('  · 느린 변수 4종 (전략이 서 있는 땅이 흔들리는가)')
        for nm, w, x, d in BANDS:
            v = cur.get(nm)
            if v is None:
                say(f'    {nm:<14} 값을 못 읽음')
                R['vars'].append({'name': nm, 'value': None, 'state': '못 읽음'})
                continue
            bad_w = (v < w) if d == 'lo' else (v > w)
            bad_x = (v < x) if d == 'lo' else (v > x)
            st = '역사 범위 밖' if bad_x else ('주의' if bad_w else '정상')
            if bad_x:
                out_of_range.append(nm)
            elif bad_w:
                warn.append(nm)
            say(f'    {nm:<14} {v:>+7.1f}%   [{st}]  (주의선 {w:+.1f}%)')
            R['vars'].append({'name': nm, 'value': v, 'state': st, 'warn_at': w})
        lvl = 3 if out_of_range else (2 if len(warn) >= 2 else (1 if warn else 0))
        MSG = {0: '정상 — 유지', 1: '주의 — 다음에 다시 확인',
               2: '경고 — 재검토 연구 개시(전략 변경 아님)',
               3: '역사 범위 밖 — 유지 여부 재검증'}
        say(f'\n  ▶ 판정: **Level {lvl} · {MSG[lvl]}**')
        R['level'], R['level_msg'] = lvl, MSG[lvl]
        if lvl >= 1:
            todo.append(f'전제 감시 Level {lvl} · {MSG[lvl]} '
                        f'(뜻은 운영_점검표.md 「자동 점검이 보는 것」)')

        # 상품 생존
        say('\n  · 4다리 상품 생존(AUM) — 살 물건이 아직 있는가')
        for ln in pick(out1, '[정상]', '[주의]', '[★경보]'):
            say('    ' + ln.strip())
            m = re.match(r'\s*(\d{6})\s+(\S.*?)\s+시총\s+([\d,]+)억\s+\[(\S+)\]', ln)
            if m:
                R['aum'].append({'code': m.group(1), 'name': m.group(2).strip(),
                                 'eok': int(m.group(3).replace(',', '')),
                                 'state': m.group(4)})
        # 경보·주의는 **종목별로** 낸다 — 어느 다리가 위태로운지가 곧 대응이다.
        # 대체 상품을 문구에 같이 실어 화면·카톡만 보고도 움직일 수 있게 한다.
        for a in R['aum']:
            if a['state'] == '정상':
                continue
            sub = SUBSTITUTE.get(a['code'], '대체 상품 미확인 — AI에게 조회 요청')
            head = ('상품 AUM 경보' if '경보' in a['state'] else '상품 AUM 주의')
            todo.append(f"{head} — {a['code']} {a['name']} 시총 {a['eok']:,}억. "
                        f"상장폐지되면 전환 자체를 못 한다. 대체: {sub}")

    # ---- [2] 체결 비용 -----------------------------------------------------
    say('\n[2/2] 체결 비용 — 0.2% 가정이 실측과 맞나')
    ok2, out2 = run(os.path.join('research', 'exec_cost.py'))
    if not ok2:
        say('  ★ 실행 실패')
        todo.append('체결비용 스크립트가 실패했다 — AI에게 알릴 것')
        R['ok'] = False
    else:
        for ln in pick(out2, '진행률', '수집', '모형 슬리피지'):
            say('  ' + ln.strip())
        m = re.search(r'진행률\s+(\d+)/(\d+)', out2)
        if m:
            R['exec']['switches'] = int(m.group(1))
            R['exec']['need'] = int(m.group(2))
        m = re.search(r'수집\s+(\d+)\s*영업일', out2)
        if m:
            R['exec']['nav_days'] = int(m.group(1))
        if '판정 가능' in out2:
            todo.append('체결비용 표본이 찼다 — 비용 가정을 실측으로 교체할 시점')
        elif '★모형 초과' in out2:
            # 표본이 아직 적을 때는 「할 일」이 아니라 관찰 기록으로만 남긴다.
            say('  ▶ 참고: 괴리가 모형을 넘지만 **표본이 부족해 판정하지 않는다.**')
            say('    손익분기가 편도 2.5%(모형의 25배)라 결론이 뒤집힐 여지는 낮다.')

    # ---- 결론 --------------------------------------------------------------
    R['todo'] = todo
    if JSON_MODE:
        print(json.dumps(R, ensure_ascii=False))
        return

    say(f'\n{THIN}')
    if todo:
        say(f' 할 일 {len(todo)}건')
        for i, t in enumerate(todo, 1):
            say(f'   {i}. {t}')
    else:
        say(' 결과: 할 일 없음 — 전부 정상.')
    say(THIN)
    say(' 이 점검은 전략을 바꾸지 않는다. 이상이 있어도 「지켜본다」가 기본이다.')
    say(' 평소엔 자동 파수꾼이 매주 대신 돌린다 — 결과는 화면 「버전 · 동결」에 뜬다.')
    say(' 자세한 설명: 같은 폴더의 운영_점검표.md\n')


if __name__ == '__main__':
    main()
