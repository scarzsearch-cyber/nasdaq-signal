# -*- coding: utf-8 -*-
"""
분기 점검 — 이것 하나만 돌리면 된다.

    python 내가_보는_것/점검.py

흩어진 정기 점검 스크립트를 한 번에 돌리고 **한국어로 결론만** 보여준다.
경로를 외울 필요도, 어느 파일을 돌릴지 고를 필요도 없다.
어느 폴더에서 실행해도 된다 — 아래 chdir 이 저장소 루트를 스스로 찾는다.

무엇을 보는가:
  [1] 전제 감시  — 전략이 아직 유효한 조건 안에 있나 (research/surv_map.py)
                   느린 변수 4종의 분포 위치 + 4다리 상품 생존(AUM)
  [2] 체결 비용  — 0.2% 가정이 실측과 맞나 (research/exec_cost.py)

언제 돌리나: **분기 1회** (1·4·7·10월 아무 때나). 급할 것 없다.
자세한 설명: 같은 폴더의 운영_점검표.md
"""
import io
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

    print(f'\n{LINE}\n 분기 점검 — {date.today()}\n{LINE}')

    # ---- [1] 전제 감시 -----------------------------------------------------
    print('\n[1/2] 전제 감시 — 전략이 아직 유효한 조건 안에 있나')
    ok1, out1 = run(os.path.join('research', 'surv_map.py'))
    if not ok1:
        print('  ★ 실행 실패 — 아래 원문을 확인하라')
        print('  ' + out1.strip().splitlines()[-1] if out1.strip() else '')
        todo.append('전제 감시 스크립트가 실패했다 — 개발자(AI)에게 원문을 보여줄 것')
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
        print('  · 느린 변수 4종 (전략이 서 있는 땅이 흔들리는가)')
        for nm, w, x, d in BANDS:
            v = cur.get(nm)
            if v is None:
                print(f'    {nm:<14} 값을 못 읽음')
                continue
            bad_w = (v < w) if d == 'lo' else (v > w)
            bad_x = (v < x) if d == 'lo' else (v > x)
            st = '역사 범위 밖' if bad_x else ('주의' if bad_w else '정상')
            if bad_x:
                out_of_range.append(nm)
            elif bad_w:
                warn.append(nm)
            print(f'    {nm:<14} {v:>+7.1f}%   [{st}]  (주의선 {w:+.1f}%)')
        lvl = 3 if out_of_range else (2 if len(warn) >= 2 else (1 if warn else 0))
        MSG = {0: '정상 — 유지', 1: '주의 — 다음 분기에 다시 확인',
               2: '경고 — 재검토 연구 개시(전략 변경 아님)',
               3: '역사 범위 밖 — 유지 여부 재검증'}
        print(f'\n  ▶ 판정: **Level {lvl} · {MSG[lvl]}**')
        if lvl >= 1:
            todo.append(f'전제 감시 Level {lvl} — {MSG[lvl]} (설명서: SURVIVAL_MONITOR §F)')

        # 상품 생존
        print('\n  · 4다리 상품 생존(AUM) — 살 물건이 아직 있는가')
        for ln in pick(out1, '[정상]', '[주의]', '[★경보]'):
            print('    ' + ln.strip())
        if '[★경보]' in out1:
            todo.append('상품 AUM 경보 — 대체 상품 확인 필요 (SURVIVAL_MONITOR §F-2)')
        elif '[주의]' in out1:
            todo.append('상품 AUM 주의 — 다음 분기에 다시 확인')

    # ---- [2] 체결 비용 -----------------------------------------------------
    print('\n[2/2] 체결 비용 — 0.2% 가정이 실측과 맞나')
    ok2, out2 = run(os.path.join('research', 'exec_cost.py'))
    if not ok2:
        print('  ★ 실행 실패')
        todo.append('체결비용 스크립트가 실패했다 — 개발자(AI)에게 알릴 것')
    else:
        for ln in pick(out2, '진행률', '수집', '모형 슬리피지'):
            print('  ' + ln.strip())
        if '판정 가능' in out2:
            todo.append('체결비용 표본이 찼다 — 비용 가정을 실측으로 교체할 시점')
        elif '★모형 초과' in out2:
            # 표본이 아직 적을 때는 「할 일」이 아니라 관찰 기록으로만 남긴다.
            print('  ▶ 참고: 괴리가 모형을 넘지만 **표본이 부족해 판정하지 않는다.**')
            print('    손익분기가 편도 2.5%(모형의 25배)라 결론이 뒤집힐 여지는 낮다.')

    # ---- 결론 --------------------------------------------------------------
    print(f'\n{THIN}')
    if todo:
        print(f' 할 일 {len(todo)}건')
        for i, t in enumerate(todo, 1):
            print(f'   {i}. {t}')
    else:
        print(' 결과: 할 일 없음 — 전부 정상. 다음 분기에 또 돌리면 된다.')
    print(THIN)
    print(' 이 점검은 전략을 바꾸지 않는다. 이상이 있어도 「지켜본다」가 기본이다.')
    print(' 자세한 설명: 같은 폴더의 운영_점검표.md\n')


if __name__ == '__main__':
    main()
