#!/usr/bin/env python3
"""괴담 인스타 자동 게시 릴레이.

동작:
1. verify/request.txt 가 있고 verify/result.json 이 더 오래됐으면 토큰/계정 검증 실행.
2. posts/*/caption.txt 가 있는데 같은 폴더에 result.json 이 없으면 캐러셀 게시 실행.

결과는 각 폴더의 result.json 에 기록된다 (성공: permalink 포함 / 실패: 오류 내용).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HOST = "https://graph.instagram.com"
VER = "v25.0"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER = os.environ["IG_USER_ID"]
REPO = os.environ.get("REPO_SLUG", "")


def api(method: str, path: str, params: dict | None = None) -> dict:
    params = dict(params or {})
    url = f"{HOST}/{VER}/{path}"
    data = None
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        data = json.dumps(params).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {body}") from e


def write_result(dirpath: str, payload: dict) -> None:
    payload["finished_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(dirpath, "result.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_verify() -> None:
    req_path = "verify/request.txt"
    res_path = "verify/result.json"
    if not os.path.exists(req_path):
        return
    if os.path.exists(res_path) and os.path.getmtime(res_path) >= os.path.getmtime(req_path):
        # git checkout이 mtime을 보존하지 않으므로 내용 비교로 재확인
        try:
            with open(res_path, encoding="utf-8") as f:
                prev = json.load(f)
            with open(req_path, encoding="utf-8") as f:
                stamp = f.read().strip()
            if prev.get("request_stamp") == stamp:
                return
        except Exception:
            pass
    with open(req_path, encoding="utf-8") as f:
        stamp = f.read().strip()
    out: dict = {"request_stamp": stamp}
    try:
        me = api("GET", "me", {"fields": "user_id,username,account_type"})
        out["me"] = me
        limit = api("GET", f"{IG_USER}/content_publishing_limit", {"fields": "quota_usage,config"})
        out["content_publishing_limit"] = limit
        out["status"] = "ok"
    except Exception as e:  # noqa: BLE001
        out["status"] = "error"
        out["error"] = str(e)
    write_result("verify", out)
    print("verify:", out.get("status"))


def publish_post(dirpath: str) -> None:
    out: dict = {"post_dir": dirpath}
    try:
        with open(os.path.join(dirpath, "caption.txt"), encoding="utf-8") as f:
            caption = f.read().strip()
        cards = sorted(
            n for n in os.listdir(dirpath)
            if n.lower().endswith((".jpg", ".jpeg")) and n.startswith("card")
        )
        if not cards:
            raise RuntimeError("no card_*.jpg files found")
        if len(cards) > 10:
            raise RuntimeError(f"too many cards: {len(cards)} (max 10)")
        alts = []
        alt_path = os.path.join(dirpath, "alts.txt")
        if os.path.exists(alt_path):
            with open(alt_path, encoding="utf-8") as f:
                alts = [ln.strip() for ln in f.read().splitlines()]

        base = f"https://raw.githubusercontent.com/{REPO}/main/{dirpath}"
        children = []
        for i, name in enumerate(cards):
            params = {
                "image_url": f"{base}/{urllib.parse.quote(name)}",
                "is_carousel_item": "true",
            }
            if i < len(alts) and alts[i]:
                params["alt_text"] = alts[i][:1000]
            cid = api("POST", f"{IG_USER}/media", params)["id"]
            children.append(cid)
            print(f"child {i + 1}/{len(cards)}: {cid}")

        carousel = api("POST", f"{IG_USER}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "is_ai_generated": "true",
        })["id"]
        print("carousel container:", carousel)

        status = None
        for _ in range(5):
            status = api("GET", carousel, {"fields": "status_code"}).get("status_code")
            print("status:", status)
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container status {status}")
            time.sleep(60)
        if status != "FINISHED":
            raise RuntimeError(f"container not ready after polling (last={status})")

        media = api("POST", f"{IG_USER}/media_publish", {"creation_id": carousel})["id"]
        info = api("GET", media, {"fields": "permalink,timestamp"})
        out.update({
            "status": "published",
            "media_id": media,
            "permalink": info.get("permalink"),
            "timestamp": info.get("timestamp"),
            "cards": len(cards),
        })
    except Exception as e:  # noqa: BLE001
        out["status"] = "error"
        out["error"] = str(e)
    write_result(dirpath, out)
    print("post:", dirpath, "->", out["status"])


def main() -> None:
    run_verify()
    if os.path.isdir("posts"):
        for d in sorted(os.listdir("posts")):
            dirpath = os.path.join("posts", d)
            if not os.path.isdir(dirpath):
                continue
            if not os.path.exists(os.path.join(dirpath, "caption.txt")):
                continue
            if os.path.exists(os.path.join(dirpath, "result.json")):
                continue
            publish_post(dirpath)


if __name__ == "__main__":
    sys.exit(main())
