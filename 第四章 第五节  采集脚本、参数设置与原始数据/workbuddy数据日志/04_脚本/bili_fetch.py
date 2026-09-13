#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站《故事新编》相关视频采集（WBI 签名 + 登录态 Cookie）

设计要点（对应论文方法论）：
- 同一关键词分别在「综合排序(totalrank)」与「最新排序(pubdate)」下采样，
  两组标签构成的差异可作为「算法排序干预可见性」的代理指标（proxy）。
- 只取搜索接口公开返回字段，不触碰后台数据。

用法:
  python bili_fetch.py --keyword "故事新编 鲁迅" --pages 5 --out <dir>
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

TID_MAP = {
    1: "动画", 13: "番剧", 167: "国创", 3: "音乐", 129: "舞蹈", 4: "游戏",
    36: "知识", 188: "科技", 234: "运动", 223: "汽车", 160: "生活", 211: "美食",
    217: "动物圈", 119: "鬼畜", 155: "时尚", 202: "资讯", 5: "娱乐",
    181: "影视", 177: "纪录片", 23: "电影", 11: "电视剧",
}

ORDERS = {"totalrank": "综合排序", "pubdate": "最新排序"}


def sanitize_cookie(c: str) -> str:
    """Cookie 值若含非 ASCII（中文昵称等），做百分号编码以免 HTTP 头编码失败。"""
    if not c:
        return ""
    out = []
    for kv in c.split(";"):
        kv = kv.strip()
        if not kv:
            continue
        if "=" in kv:
            k, v = kv.split("=", 1)
            if any(ord(ch) > 127 for ch in v):
                v = urllib.parse.quote(v, safe="")
            out.append(f"{k}={v}")
        else:
            out.append(kv)
    return "; ".join(out)


def http_json(url, params=None, cookie="", timeout=25, referer="https://www.bilibili.com/"):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Cookie": cookie,
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def get_mixin_key(cookie: str):
    """从 nav 接口取 img_key/sub_key，生成 wbi mixin_key。"""
    j = http_json(NAV_URL, cookie=cookie, referer="https://www.bilibili.com/")
    wbi = (j.get("data") or {}).get("wbi_img") or {}
    img_url = wbi.get("img_url", "")
    sub_url = wbi.get("sub_url", "")
    if not img_url or not sub_url:
        raise RuntimeError(f"nav 未返回 wbi_img: {j.get('code')} {j.get('message')}")
    img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
    raw = img_key + sub_key
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def enc_wbi(params: dict, mixin_key: str) -> dict:
    params = dict(params)
    params.pop("w_rid", None)
    params["wts"] = int(time.time())
    query = urllib.parse.urlencode(sorted(params.items()))
    params["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    return params


def search_page(keyword, order, page, mixin_key, cookie, page_size=20):
    base = {
        "search_type": "video",
        "keyword": keyword,
        "order": order,
        "page": page,
        "page_size": page_size,
    }
    signed = enc_wbi(base, mixin_key)
    j = http_json(SEARCH_URL, signed, cookie=cookie)
    if j.get("code") != 0:
        raise RuntimeError(f"搜索失败 code={j.get('code')} msg={j.get('message')}")
    return (j.get("data") or {}).get("result") or []


def norm(item):
    tags = [t.strip() for t in (item.get("tag") or "").split(",") if t.strip()]
    tid = item.get("typeid") or item.get("tid")
    return {
        "bvid": item.get("bvid"),
        "aid": item.get("aid"),
        "title": (item.get("title") or "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
        "author": item.get("author"),
        "mid": item.get("mid"),
        "play": item.get("play"),
        "danmaku": item.get("video_review"),
        "like": item.get("like"),
        "favorites": item.get("favorites"),
        "pubdate": item.get("pubdate"),
        "duration": item.get("duration"),
        "tid": tid,
        "tid_name": TID_MAP.get(tid, str(tid)),
        "tags": tags,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="故事新编 鲁迅")
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--delay", default="2-4")
    ap.add_argument("--cookie-file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cookie = sanitize_cookie(open(args.cookie_file, encoding="utf-8", errors="ignore").read().strip())
    os.makedirs(args.out, exist_ok=True)
    a, b = (float(x) for x in args.delay.split("-"))
    t0 = time.time()

    mixin_key = get_mixin_key(cookie)
    print(f"WBI mixin_key 获取成功: {mixin_key[:8]}...", flush=True)

    seen, out = set(), []
    for order, label in ORDERS.items():
        print(f"\n=== {label} (order={order}) ===", flush=True)
        for p in range(1, args.pages + 1):
            try:
                res = search_page(args.keyword, order, p, mixin_key, cookie)
            except Exception as e:
                print(f"  page={p} ERR: {e}", flush=True)
                break
            added = 0
            for it in res:
                r = norm(it)
                if not r["bvid"] or r["bvid"] in seen:
                    continue
                seen.add(r["bvid"])
                r["_order"] = order
                r["_keyword"] = args.keyword
                r["_fetched_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                out.append(r)
                added += 1
            print(f"  page={p}: 返回 {len(res)} 条 / 新增 {added} 条 / 累计 {len(out)}", flush=True)
            if not res:
                break
            time.sleep(random.uniform(a, b))

    slug = args.keyword.replace(" ", "")
    jsonl = os.path.join(args.out, f"bili_{slug}.jsonl")
    with open(jsonl, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = {
        "keyword": args.keyword,
        "orders": list(ORDERS.keys()),
        "pages_per_order": args.pages,
        "collected": len(out),
        "by_order": {o: sum(1 for r in out if r["_order"] == o) for o in ORDERS},
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "仅取搜索接口公开字段；综合排序与最新排序的差异可作算法排序干预的代理指标。",
    }
    with open(os.path.join(args.out, f"bili_{slug}_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("\n---- 采集完成 ----")
    print(f"关键词     : {args.keyword}")
    print(f"总条数     : {len(out)}  按排序: {meta['by_order']}")
    print(f"落盘       : {jsonl}")

    from collections import Counter
    for o, lab in ORDERS.items():
        c = Counter(t for r in out if r["_order"] == o for t in r["tags"])
        print(f"\n[{lab}] 高频标签 Top15:")
        for t, n in c.most_common(15):
            print(f"   {t}: {n}")


if __name__ == "__main__":
    main()
