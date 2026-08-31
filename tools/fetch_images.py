#!/usr/bin/env python3
"""從每則新聞的原始網址抓 og:image，裁成需要的尺寸並轉成 WebP。

用法：
    python3 tools/fetch_images.py data/2026-08-26.json

產出：
    images/cache/<hash>.orig      原圖（重跑時直接沿用，不重抓）
    images/<hash>-<size>.webp     裁切壓縮後的成品
    images/manifest.json          網址 -> 各尺寸檔名；抓不到的記成 null

抓不到圖是正常的（付費牆、Cloudflare、無 og:image）。
版面對 null 有對應的無圖樣式，不會開天窗。
"""
import concurrent.futures as futures
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "images", "cache")
OUT = os.path.join(ROOT, "images")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
}

# 各版位需要的尺寸：名稱 -> (寬, 高)。高 = 0 代表正方形縮圖
SIZES = {
    "xl": (880, 495),   # 今日焦點頭條
    "lg": (560, 315),   # 各段焦點頭條 / 重點新聞
    "md": (460, 259),   # 股市卡片
    "sq": (128, 128),   # 清單小縮圖
}
MIN_SOURCE_WIDTH = 320


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


class FetchError(Exception):
    pass


def get(url, timeout=12, limit=600_000):
    """透過 curl 抓取，不用 urllib。

    本機環境下純粹是慣用法選擇，curl 比較好除錯。

    雲端排程的沙盒對新聞網域的出網請求，會被出網代理直接擋在 CONNECT 層級
    （回 403，`__agentproxy/status` 可查到白名單不含任意第三方網域）——這是
    網路層的網域白名單限制，換 curl 或 urllib 結果一樣，不是這支程式能繞過的。
    雲端環境的這步預期就是整批失敗，照 RUNBOOK 的錯誤處理繼續走純文字版面即可。
    """
    with tempfile.TemporaryDirectory() as tmp:
        body_path = os.path.join(tmp, "body")
        header_path = os.path.join(tmp, "headers")
        cmd = ["curl", "-sL", "--max-time", str(timeout), "-A", UA]
        for k, v in HEADERS.items():
            if k != "User-Agent":
                cmd += ["-H", f"{k}: {v}"]
        cmd += ["-o", body_path, "-D", header_path,
                "-w", "%{url_effective}", url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if r.returncode != 0 or not os.path.exists(body_path):
            raise FetchError(f"curl exit {r.returncode}: {r.stderr.strip()[:200]}")
        final_url = r.stdout.strip() or url
        ctype = ""
        if os.path.exists(header_path):
            headers = open(header_path, encoding="utf-8", errors="ignore").read()
            # 有重導向的話會有好幾組標頭，Content-Type 取最後一組回應的
            for line in headers.splitlines():
                if line.lower().startswith("content-type:"):
                    ctype = line.split(":", 1)[1].strip()
        with open(body_path, "rb") as f:
            data = f.read(limit)
        return data, ctype, final_url


META = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](og:image(?::secure_url|:url)?|twitter:image(?::src)?)["\'][^>]*>',
    re.I,
)
CONTENT = re.compile(r'content=["\']([^"\']+)["\']', re.I)


LD_BLOCK = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)
IMAGE_SRC = re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]*>', re.I)

# 只從這些容器開始往後找內文圖，避免抓到側欄推薦或廣告的無關照片。
# 巢狀 div 沒辦法用正則配對，所以改成「從容器開頭往後看一段」。
ARTICLE_START = re.compile(
    r'<(?:article|main)\b'
    r'|<div[^>]+(?:class|id)=["\'][^"\']*'
    r'(?:article-?(?:body|content|main)|post_body|content_desc|left_zw|entry-content|story-body|main-?content)'
    r'[^"\']*["\']',
    re.I,
)
ARTICLE_WINDOW = 30_000
IMG_TAG = re.compile(r'<img[^>]+>', re.I)
SRC_ATTR = re.compile(r'(?:data-src|data-original|src)=["\']([^"\']+)["\']', re.I)
JUNK = re.compile(
    r'logo|icon|avatar|qrcode|ewm|erweima|banner|ad[sv]?[-_/]|spacer|blank|'
    r'placeholder|share|weibo|wechat|button|nav|footer|header|\.svg|\.gif',
    re.I,
)


def absolutize(u, base):
    if not u:
        return None
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base)
        return (m.group(1) if m else "") + u
    return u if u.startswith("http") else None


def _ld_images(node, out):
    """JSON-LD 的 image 欄位型態很雜：字串、陣列、或 {url: ...}，全部收進來。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() == "image":
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, dict) and isinstance(v.get("url"), str):
                    out.append(v["url"])
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, str):
                            out.append(x)
                        elif isinstance(x, dict) and isinstance(x.get("url"), str):
                            out.append(x["url"])
            else:
                _ld_images(v, out)
    elif isinstance(node, list):
        for x in node:
            _ld_images(x, out)


def find_image(html, base):
    """依可信度排序找配圖：og / twitter -> JSON-LD -> image_src -> 文章內文第一張。"""
    cands = []
    for m in META.finditer(html):
        c = CONTENT.search(m.group(0))
        if c:
            cands.append((m.group(1).lower(), unescape(c.group(1))))
    cands.sort(key=lambda kv: 0 if kv[0].startswith("og:") else 1)
    for _, u in cands:
        if a := absolutize(u, base):
            return a, "og"

    for m in LD_BLOCK.finditer(html):
        try:
            found = []
            _ld_images(json.loads(m.group(1).strip()), found)
        except Exception:
            continue
        for u in found:
            if a := absolutize(unescape(u), base):
                return a, "ld+json"

    if m := IMAGE_SRC.search(html):
        if c := re.search(r'href=["\']([^"\']+)["\']', m.group(0), re.I):
            if a := absolutize(unescape(c.group(1)), base):
                return a, "image_src"

    for m in ARTICLE_START.finditer(html):
        body = html[m.start(): m.start() + ARTICLE_WINDOW]
        for tag in IMG_TAG.finditer(body):
            s = SRC_ATTR.search(tag.group(0))
            if not s or JUNK.search(s.group(1)):
                continue
            if a := absolutize(unescape(s.group(1)), base):
                return a, "article body"
    return None, None


# 影像處理有兩套後端。Pillow 是主要的：跨平台，而且 webp/avif 讀寫都自己來，
# 不需要外部指令。macOS 上沒裝 Pillow 時退回 sips + cwebp。
# 這件事重要是因為排程若要跑在雲端（Linux），sips 根本不存在。
try:
    from PIL import Image, ImageOps
    BACKEND = "pillow"
except ImportError:
    Image = ImageOps = None
    BACKEND = "sips"


def sips(*args):
    subprocess.run(["sips", *args], capture_output=True, check=True)


def dims(path):
    if BACKEND == "pillow":
        try:
            with Image.open(path) as im:
                return im.size
        except Exception:
            return (0, 0)
    r = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
        capture_output=True, text=True,
    )
    w = re.search(r"pixelWidth: (\d+)", r.stdout)
    h = re.search(r"pixelHeight: (\d+)", r.stdout)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def normalize(orig, key):
    """來源可能是 webp/avif/png，統一轉成 JPEG 工作檔再處理。

    Pillow 其實可以直接讀原檔，但保留這一步讓兩套後端流程一致，
    也順便把 EXIF 轉向、調色盤、透明背景一次處理掉。
    """
    work = os.path.join(CACHE, key + ".work.jpg")
    if os.path.exists(work):
        return work
    if BACKEND == "pillow":
        try:
            with Image.open(orig) as im:
                im = ImageOps.exif_transpose(im)
                if im.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    im = im.convert("RGBA")
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                im.convert("RGB").save(work, "JPEG", quality=92)
            return work
        except Exception:
            return None
    try:
        sips("-s", "format", "jpeg", orig, "--out", work)
    except subprocess.CalledProcessError:
        return None
    return work


def derive(work, key, name, tw, th, quality=68):
    """把工作檔置中裁成 tw×th 再轉 WebP。"""
    dst = os.path.join(OUT, f"{key}-{name}.webp")
    if os.path.exists(dst):
        return os.path.basename(dst)

    if BACKEND == "pillow":
        try:
            with Image.open(work) as im:
                # 短邊縮到剛好蓋滿再置中裁切，避免變形
                ImageOps.fit(im, (tw, th), Image.LANCZOS, centering=(0.5, 0.5)) \
                        .save(dst, "WEBP", quality=quality, method=6)
            return os.path.basename(dst)
        except Exception:
            return None

    tmp = os.path.join(CACHE, f"{key}-{name}.jpg")
    try:
        subprocess.run(["cp", work, tmp], check=True)
        w, h = dims(tmp)
        if not w:
            return None
        if w / h > tw / th:
            sips("--resampleHeight", str(th), tmp)
        else:
            sips("--resampleWidth", str(tw), tmp)
        sips("-c", str(th), str(tw), tmp)
        r = subprocess.run(
            ["cwebp", "-quiet", "-q", str(quality), "-m", "6", tmp, "-o", dst],
            capture_output=True,
        )
        return os.path.basename(dst) if r.returncode == 0 and os.path.exists(dst) else None
    except subprocess.CalledProcessError:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def fetch_one(url):
    key = key_of(url)
    orig = os.path.join(CACHE, key + ".orig")
    note = "cached"
    if not os.path.exists(orig):
        try:
            body, ctype, final = get(url, limit=1_200_000)
        except Exception as e:
            return url, None, f"page failed: {type(e).__name__}"
        img_url, how = find_image(body.decode("utf-8", "ignore"), final)
        if not img_url:
            return url, None, "找不到配圖"
        try:
            data, ctype, _ = get(img_url, limit=8_000_000)
        except Exception as e:
            return url, None, f"image failed: {type(e).__name__}"
        if not data or "image" not in ctype.lower():
            return url, None, f"not an image ({ctype[:30]})"
        with open(orig, "wb") as f:
            f.write(data)
        note = how
    w, _ = dims(orig)
    if w < MIN_SOURCE_WIDTH:
        return url, None, f"too small ({w}px)"
    work = normalize(orig, key)
    if not work:
        return url, None, "unreadable format"
    made = {}
    for name, (tw, th) in SIZES.items():
        out = derive(work, key, name, tw, th)
        if out:
            made[name] = out
    return url, (made or None), note


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    urls, seen = [], set()
    for grp in ("top3", "global", "twcn", "market"):
        for item in data.get(grp, []):
            u = item.get("url")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)

    os.makedirs(CACHE, exist_ok=True)
    mpath = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}

    ok = 0
    with futures.ThreadPoolExecutor(max_workers=10) as ex:
        for url, made, note in ex.map(fetch_one, urls):
            manifest[url] = made
            if made:
                ok += 1
            else:
                print(f"  ✗ {note:34s} {url[:78]}")

    json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n抓到配圖 {ok}/{len(urls)} 則")


if __name__ == "__main__":
    main()
