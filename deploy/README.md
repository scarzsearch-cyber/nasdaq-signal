# 폰에서 보기 + 종가 자동 갱신 (GitHub Pages + Actions)

완성되면 이렇게 된다:

- 매일 한국시간 **07:30경 GitHub 서버가 알아서** QQQ 종가를 받아 신호를 계산하고 커밋
- 폰에서 URL 하나 열면 **오늘 뭘 들고 있어야 하는지**만 보임 (입력할 것 없음)
- 무료. 내 PC를 켜둘 필요 없음

---

## 사전 준비

1. **GitHub 계정** — 없으면 https://github.com 에서 가입
2. **GitHub CLI** 설치 후 로그인
   ```bash
   # macOS
   brew install gh
   # Windows
   winget install GitHub.cli
   # Ubuntu/Debian
   sudo apt install gh

   gh auth login          # 브라우저로 로그인, 안내대로 진행
   ```

---

## Claude Code에 붙여넣을 프롬프트

압축 푼 폴더에서 `claude` 실행 후 아래를 그대로 붙여넣는다.

```
이 폴더를 GitHub 저장소로 만들고 GitHub Pages + Actions로 배포해서,
폰에서 링크로 신호를 볼 수 있고 매일 종가가 자동 갱신되게 해줘.

준비된 파일:
- signal.html          : 신호 화면 (data/signal.json 있으면 자동 로드, 없으면 수동 입력)
- deploy/update_signal.py : stooq에서 QQQ 종가 받아 data/signal.json 갱신
- deploy/workflows/daily-signal.yml : 매일 22:30 UTC(=KST 07:30) 자동 실행
- deploy/workflows/pages.yml        : main 푸시시 Pages 배포

해야 할 일:
1. deploy/workflows/*.yml 을 .github/workflows/ 로 옮겨라
2. python3 deploy/update_signal.py 를 한 번 실행해 data/signal.json이
   정상 생성되는지 확인해라 (stooq 접속이 되는지 여기서 판가름난다)
3. .gitignore를 만들어 불필요한 파일(__pycache__ 등)을 제외해라.
   단 data/ 폴더는 반드시 커밋 대상에 포함시켜라 (Actions가 여기에 결과를 쓴다)
4. gh repo create 로 저장소를 만들고 푸시해라.
   저장소 이름은 nasdaq-signal 로 해라
5. GitHub Pages를 활성화해라 (Settings > Pages > Source를 GitHub Actions로)
   gh api 로 처리할 수 있으면 그렇게 하고, 안 되면 내가 눌러야 할 위치를 정확히 알려줘라
6. Actions 워크플로를 수동으로 한 번 실행(workflow_dispatch)해서 정상 동작을 확인해라
7. 배포된 URL을 알려줘라

주의:
- 워크플로에 permissions: contents: write 가 있어야 커밋이 된다. 이미 넣어뒀다
- Actions가 커밋을 푸시하려면 Settings > Actions > General >
  Workflow permissions 가 "Read and write permissions" 여야 한다.
  gh로 설정 가능하면 해주고, 안 되면 위치를 알려줘라
- 무료 계정은 private 저장소에 Pages를 못 쓴다. public으로 만들되,
  개인정보는 전혀 없고 공개 주가 데이터와 신호만 들어간다는 점을 확인해줘라
```

---

## 완료 후 — 폰에 앱처럼 추가

배포 URL은 보통 `https://<계정명>.github.io/nasdaq-signal/` 형태다.

- **iPhone (Safari)**: URL 열기 → 공유 버튼 → "홈 화면에 추가"
- **Android (Chrome)**: URL 열기 → 우상단 ⋮ → "홈 화면에 추가"

---

## 동작 방식

```
매일 22:30 UTC (= 한국 07:30)
  └ GitHub Actions 실행
      └ deploy/update_signal.py
          ├ stooq에서 QQQ 전체 일별 종가 다운로드
          ├ data/qqq.csv 갱신 (기존 데이터와 병합)
          ├ 252일 낙폭 계산 → 상태머신(−16%/−11%) 통과
          └ data/signal.json 저장 (현재 상태 + 최근 12일 + 위기 궤적)
      └ 변경분 자동 커밋 & 푸시
          └ pages.yml이 트리거되어 사이트 재배포
```

미국장 마감은 20:00(서머타임) 또는 21:00 UTC라 22:30이면 여유가 있고,
한국장 개장(09:00 KST)보다 1시간 30분 앞선다.

휴장일에는 새 종가가 없어 커밋이 생략된다(정상).

---

## 확인 / 문제 해결

```bash
# 로컬에서 수동 실행 (Actions 없이 테스트)
python3 deploy/update_signal.py

# Actions 실행 이력 보기
gh run list --workflow=daily-signal.yml

# 마지막 실행 로그
gh run view --log

# 수동으로 지금 한 번 돌리기
gh workflow run daily-signal.yml
```

**stooq가 403을 뱉으면** — 접속 차단이다. `deploy/update_signal.py`의 `SRC`를
다른 소스로 바꿔야 한다. Claude Code에 "stooq가 막혔으니 대체 데이터 소스로
바꿔줘"라고 하면 된다. 이 경우에도 `data/qqq.csv` 캐시가 있으면 스크립트는
죽지 않고 캐시로 동작한다.

**Actions가 커밋을 못 하면** — Settings > Actions > General >
Workflow permissions 를 "Read and write permissions"로 바꾼다.

**cron이 정시에 안 돌면** — GitHub Actions의 스케줄은 부하에 따라 최대
수십 분 지연될 수 있다. 07:30은 한국장 개장까지 여유가 있어 문제되지 않는다.

---

## 주의

- 배포된 페이지는 **URL을 아는 사람이면 누구나** 볼 수 있다. 개인정보는 없지만
  전략 문턱값(−16%/−11%)은 노출된다. 신경 쓰이면 GitHub Pro(유료)로 private
  저장소를 쓰거나, 다른 정적 호스팅(Vercel/Netlify의 비공개 배포)을 검토한다.
- 이 화면은 **판정만** 한다. 실제 매매는 직접 해야 한다.
