#!/usr/bin/env python3
"""npm 패키지(@lemoon123141/gwedam-posts)에서 새 포스트를 받아 repo에 반영.

Cowork 예약 세션은 카드 이미지+캡션을 npm 패키지 버전으로 publish한다.
이 스크립트는 최근 버전들의 tarball을 내려받아, repo에 아직 없는
posts/<id>/ 디렉터리를 추가한다. 이후 publish.py가 게시를 수행한다.
"""
import io
import json
import os
import shutil
import tarfile
import urllib.request

PKG = "@lemoon123141/gwedam-posts"
REG = "https://registry.npmjs.org"
MAX_VERSIONS = 20


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> None:
    quoted = PKG.replace("/", "%2f")
    try:
        meta = fetch_json(f"{REG}/{quoted}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("package not published yet; nothing to sync")
            return
        raise
    versions = list(meta.get("versions", {}).keys())[-MAX_VERSIONS:]
    added = 0
    for ver in versions:
        tarball = meta["versions"][ver]["dist"]["tarball"]
        with urllib.request.urlopen(tarball, timeout=120) as r:
            data = r.read()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            members = [m for m in tf.getmembers()
                       if m.name.startswith("package/posts/") and m.isfile()]
            post_dirs = {m.name.split("/")[2] for m in members if len(m.name.split("/")) > 3}
            for pid in post_dirs:
                dest = os.path.join("posts", pid)
                if os.path.exists(os.path.join(dest, "caption.txt")):
                    continue  # 이미 반영됨
                os.makedirs(dest, exist_ok=True)
                for m in members:
                    parts = m.name.split("/")
                    if len(parts) > 3 and parts[2] == pid:
                        fname = os.path.basename(m.name)
                        if not fname or ".." in fname:
                            continue
                        src = tf.extractfile(m)
                        if src is None:
                            continue
                        with open(os.path.join(dest, fname), "wb") as out:
                            shutil.copyfileobj(src, out)
                print(f"synced {dest} (from {ver})")
                added += 1
    print(f"sync done: {added} new post dir(s)")


if __name__ == "__main__":
    main()
