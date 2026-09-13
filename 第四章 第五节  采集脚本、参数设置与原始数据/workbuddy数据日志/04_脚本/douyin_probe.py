# -*- coding: utf-8 -*-
"""抖音采集可行性探测：搜索页 SSR / web 搜索接口，限时记录结果。"""
import json, os, re, sys, urllib.parse, urllib.request, urllib.error, gzip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE = open(os.path.join(ROOT, "douyin_cookie.txt"),
              encoding="utf-8", errors="replace").read().strip()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def san(raw):
    return "".join(c if ord(c) < 128 else urllib.parse.quote(c.encode()) for c in raw)


def get(url, extra=None):
    h = {"User-Agent": UA, "Cookie": san(COOKIE),
         "Referer": "https://www.douyin.com/", "Accept": "*/*",
         "Accept-Encoding": "gzip, deflate"}
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return r.status, body.decode("utf-8", errors="replace")


def probe(name, url):
    try:
        st, txt = get(url)
        print(f"=== {name} HTTP {st} len={len(txt)}")
        m = re.search(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', txt, re.S)
        if m:
            data = urllib.parse.unquote(m.group(1))
            print("  RENDER_DATA found, decoded len:", len(data))
            print("  head:", data[:300])
            return data
        for pat in ['"aweme_id"', '"desc"', 'verify', '验证码', 'sec_sdk']:
            if pat in txt:
                print("  contains:", pat)
        print("  head:", txt[:200].replace("\n", " "))
    except urllib.error.HTTPError as e:
        print(f"=== {name} HTTP {e.code}")
        print("  ", e.read()[:200])
    except Exception as e:
        print(f"=== {name} ERR {type(e).__name__}: {e}")
    return None


kw = urllib.parse.quote("故事新编 鲁迅")
probe("SSR-search", f"https://www.douyin.com/search/{kw}?type=video")
q = urllib.parse.urlencode({
    "keyword": "故事新编 鲁迅", "count": 10, "offset": 0,
    "device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web",
})
probe("API-search-item", f"https://www.douyin.com/aweme/v1/web/search/item/?{q}")
