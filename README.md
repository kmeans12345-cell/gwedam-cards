# gwedam-cards

괴담 인스타그램(@jeogdanghitteodeulja) 자동 게시 릴레이 저장소.

- `posts/<YYYY-MM-DD_HHMM_제목>/` 에 `card_01.jpg …` + `caption.txt`(+ 선택 `alts.txt`)를 push하면 GitHub Actions가 Instagram Graph API로 캐러셀을 게시하고 같은 폴더에 `result.json`을 기록한다.
- 예약 세션은 npm 패키지 `@lemoon123141/gwedam-posts`로 포스트를 업로드하며, Actions가 15분 간격(UTC 9-15시)으로 동기화·게시한다.
- `verify/request.txt` 내용을 바꿔 push하면 토큰·계정 검증만 실행되어 `verify/result.json`에 기록된다.
- 액센스 토큰은 저장소 Secret `IG_ACCESS_TOKEN`에 있음 (60일마다 갱신 필요).

이 저장소는 Claude(Cowork) 예약 작업이 자동으로 사용한다.
