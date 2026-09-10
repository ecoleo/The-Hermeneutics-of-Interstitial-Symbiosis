#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
douban_fetch.py — 豆瓣读书短评采集器（零第三方依赖）

采集指定图书在「读过」(status=P) 分类下的短评，落盘为 JSONL + meta.json。

用法示例
--------
  # 1) 先按书名查条目 ID
  python douban_fetch.py --query 故事新编

  # 2) 抓取「读过」短评（默认热门+最新双排序合并去重）
  python douban_fetch.py --id 2046909 --out ./data

  # 3) 登录态抓取（可突破未登录深度限制，见下面说明）
  python douban_fetch.py --id 2046909 --cookie "ll=...; bid=...; dbcl2=..." --out ./data

  # 4) 只抓热门排序、限制页数、加大间隔
  python douban_fetch.py --id 2046909 --sort hot --max-pages 5 --delay 6 --out ./data

重要限制（务必知悉）
-------------------
* 豆瓣对短评列表有访问深度限制：未登录时通常只能翻到第 9 页左右（约 180 条，
  start=180 起返回 403「你没有权限访问这个页面」）。带 Cookie 的登录态可显著
  提高上限，但同样受风控约束（可能出现验证码 / 临时封禁）。
* 豆瓣 www 域 robots.txt 声明 Crawl-delay: 5，book 子域无 robots.txt。
  本脚本默认 4~7 秒随机间隔 + 403 指数退避，请勿调低。
* 「全部短评」在技术上通常不可达，脚本会把「页面声明的总数」与「实际抓取数」
  一并写入 meta.json，覆盖率必须如实报告，不得含糊。
* 仅用于个人研究/教学目的的小规模采集，禁止并发轰炸、禁止绕过验证码。

Cookie 获取方式
---------------
浏览器登录豆瓣 → 打开任意豆瓣页面 → F12 → Network → 选中任意请求 →
Request Headers → 复制 Cookie 整行 → 用 --cookie 传入，或存入文件用
--cookie-file 读取（推荐，避免命令行泄漏）。
"""

import argparse
import gzip
import html as html_mod
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

STATUS_MAP = {"P": "读过", "F": "想读", "N": "在读"}
SORT_MAP = {"hot": "new_score", "time": "time"}


# ---------------------------------------------------------------- HTTP 基础
def build_opener(cookie: str = ""):
    headers = [
        ("User-Agent", UA),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "zh-CN,zh;q=0.9"),
        ("Accept-Encoding", "gzip, deflate"),
        ("Connection", "keep-alive"),
    ]
    if cookie:
        headers.append(("Cookie", cookie))
    op = urllib.request.build_opener()
    op.addheaders = headers
    return op


def http_get(opener, url, timeout=25):
    """返回 (html_text, http_code)。403/异常向上抛出由调用方退避。"""
    req = urllib.request.Request(url)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            code = resp.getcode()
            if resp.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return raw.decode("utf-8", errors="ignore"), code
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return body, e.code
    except Exception as e:
        return "", -1


def looks_blocked(html_text, code):
    if code in (403, 429, -1):
        return True
    if "你没有权限访问这个页面" in html_text:
        return True
    if "检测到有异常请求" in html_text or "sec.douban" in html_text:
        return True
    return False


# ---------------------------------------------------------------- 解析
def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html_mod.unescape(s).strip()


def parse_comments(html_text: str):
    """按 comment-item 块切分，逐块抽取字段。返回 list[dict]。"""
    starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r'<li\s+class="comment-item"\s+data-cid="(\d+)"', html_text)
    ]
    if not starts:
        return []
    out = []
    for i, (pos, cid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(html_text)
        blk = html_text[pos:end]

        def g(pat, cast=str, default=None):
            m = re.search(pat, blk, flags=re.S)
            if not m:
                return default
            try:
                return cast(m.group(1))
            except Exception:
                return default

        user = g(r'class="comment-info"[\s\S]*?<a[^>]+people/[^>]+>\s*([^<]+?)\s*</a>')
        stars = g(r'class="user-stars\s+allstar(\d)0\s+rating"', int)
        rtitle = g(r'class="user-stars[^"]*"\s+title="([^"]+)"')
        votes = g(r'class="vote-count">\s*(\d+)\s*<', int, 0)
        ctime = g(r'class="comment-time"[^>]*>\s*([^<]+?)\s*<')
        loc = g(r'class="comment-location"[^>]*>\s*([^<]+?)\s*<')
        mtext = re.search(r'<span class="short">([\s\S]*?)</span>', blk)
        text = strip_tags(mtext.group(1)) if mtext else ""
        text = re.sub(r"[ \t]+", " ", text).strip()

        if not text:
            continue
        out.append(
            {
                "cid": cid,
                "user": (user or "").strip(),
                "rating": stars if stars in (1, 2, 3, 4, 5) else None,
                "rating_title": rtitle or "",
                "votes": votes or 0,
                "time": (ctime or "").strip(),
                "location": (loc or "").strip(),
                "text": text,
            }
        )
    return out


def parse_total(html_text: str, status: str):
    """从 tab 上读取各状态声明的总数，用于计算覆盖率。"""
    label = STATUS_MAP.get(status, "读过")
    m = re.search(re.escape(label) + r"\((\d+)\)", html_text)
    return int(m.group(1)) if m else None


def parse_book_title(html_text: str):
    m = re.search(r"<title>(.*?)</title>", html_text, flags=re.S)
    t = strip_tags(m.group(1)) if m else ""
    return re.sub(r"\s*短评\s*$", "", t).strip()


# ---------------------------------------------------------------- 条目检索
def search_subject(query: str):
    url = "https://book.douban.com/j/subject_suggest?q=" + urllib.parse.quote(query)
    op = build_opener()
    body, code = http_get(op, url)
    items = []
    try:
        data = json.loads(body)
        for d in data:
            if d.get("type") == "b":
                items.append(
                    {
                        "id": d.get("id"),
                        "title": d.get("title"),
                        "author": d.get("author_name", ""),
                        "year": d.get("year", ""),
                        "url": d.get("url", ""),
                    }
                )
    except Exception:
        pass
    return items


# ---------------------------------------------------------------- 主流程
def crawl(subject_id, status="P", sorts=("new_score",), max_pages=50,
          delay=(4.0, 7.0), cookie="", out_dir=".", keep_html=False, verbose=True):
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, f"comments_{subject_id}_{status}.jsonl")
    meta_path = os.path.join(out_dir, f"meta_{subject_id}_{status}.json")
    raw_dir = os.path.join(out_dir, "raw")
    if keep_html:
        os.makedirs(raw_dir, exist_ok=True)

    seen = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("cid"):
                        seen.add(d["cid"])
                except Exception:
                    pass
        if verbose:
            print(f"[续传] 已有 {len(seen)} 条，将跳过重复。", flush=True)

    opener = build_opener(cookie)
    total_declared = None
    book_title = ""
    new_count = 0
    blocked_streak = 0
    fh = open(jsonl_path, "a", encoding="utf-8")
    t0 = time.time()

    try:
        for sort in sorts:
            if verbose:
                print(f"\n=== 排序 {sort} ===", flush=True)
            empty_streak = 0
            for page in range(max_pages):
                start = page * 20
                url = (f"https://book.douban.com/subject/{subject_id}/comments/"
                       f"?start={start}&limit=20&status={status}&sort={sort}")
                body, code = http_get(opener, url)

                if looks_blocked(body, code):
                    blocked_streak += 1
                    wait = min(60 * blocked_streak, 180)
                    print(f"  [阻断] start={start} code={code} → 退避 {wait}s"
                          f"（第 {blocked_streak} 次）", flush=True)
                    if blocked_streak >= 3:
                        print("  连续阻断 3 次，停止该排序。", flush=True)
                        break
                    time.sleep(wait)
                    continue

                blocked_streak = 0
                if total_declared is None:
                    total_declared = parse_total(body, status)
                if not book_title:
                    book_title = parse_book_title(body)
                if keep_html:
                    with open(os.path.join(raw_dir, f"{subject_id}_{status}_{sort}_{start}.html"),
                              "w", encoding="utf-8") as rf:
                        rf.write(body)

                items = parse_comments(body)
                if not items:
                    empty_streak += 1
                    print(f"  start={start} 无数据（{empty_streak}）", flush=True)
                    if empty_streak >= 2:
                        break
                else:
                    empty_streak = 0
                    added = 0
                    for it in items:
                        if it["cid"] in seen:
                            continue
                        seen.add(it["cid"])
                        it["_sort"] = sort
                        it["_fetched_at"] = datetime.now().isoformat(timespec="seconds")
                        fh.write(json.dumps(it, ensure_ascii=False) + "\n")
                        added += 1
                    new_count += added
                    fh.flush()
                    print(f"  start={start:>4} 解析 {len(items):>2} 条 / 新增 {added:>2} 条"
                          f" / 累计 {len(seen)}", flush=True)

                time.sleep(random.uniform(*delay))
    finally:
        fh.close()

    meta = {
        "subject_id": subject_id,
        "book_title": book_title,
        "status": status,
        "status_label": STATUS_MAP.get(status, status),
        "sorts": list(sorts),
        "collected": len(seen),
        "declared_total": total_declared,
        "coverage": (round(len(seen) / total_declared, 4) if total_declared else None),
        "logged_in": bool(cookie),
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_sec": round(time.time() - t0, 1),
        "comment_url": f"https://book.douban.com/subject/{subject_id}/comments/?status={status}",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if verbose:
        print("\n---- 采集完成 ----")
        print(f"条目       : {book_title}  (#{subject_id})")
        print(f"分类       : {meta['status_label']}")
        print(f"实际抓取   : {len(seen)} 条（本次新增 {new_count}）")
        print(f"页面声明   : {total_declared} 条")
        cov = f"{meta['coverage']*100:.2f}%" if meta["coverage"] else "未知"
        print(f"覆盖率     : {cov}")
        print(f"落盘       : {jsonl_path}")
        print(f"元信息     : {meta_path}")
        if not cookie:
            print("\n提示：未登录态通常只能取到前 ~180 条。带 Cookie 重跑可提高深度。")
    return meta


def main():
    ap = argparse.ArgumentParser(description="豆瓣读书短评采集器")
    ap.add_argument("--query", help="按书名搜索条目 ID（只搜索不抓取）")
    ap.add_argument("--id", dest="subject_id", help="豆瓣图书 subject ID")
    ap.add_argument("--status", default="P", choices=["P", "F", "N"],
                    help="P=读过(默认) F=想读 N=在读")
    ap.add_argument("--sort", default="both", choices=["hot", "time", "both"],
                    help="hot=热门 time=最新 both=两者合并去重(默认)")
    ap.add_argument("--max-pages", type=int, default=50, help="每种排序最多翻多少页")
    ap.add_argument("--delay", default="4-7", help="请求间隔秒数范围，如 4-7")
    ap.add_argument("--cookie", default="", help='豆瓣 Cookie 字符串（或用 --cookie-file）')
    ap.add_argument("--cookie-file", default="", help="存放 Cookie 的文件路径")
    ap.add_argument("--out", default="./douban_data", help="输出目录")
    ap.add_argument("--keep-html", action="store_true", help="保留原始 HTML 备查")
    args = ap.parse_args()

    if args.query:
        items = search_subject(args.query)
        if not items:
            print("未检索到条目。")
            return
        print(f"检索「{args.query}」得到 {len(items)} 个图书条目：\n")
        for it in items:
            print(f"  ID={it['id']:<12} {it['title']}  / {it['author']} / {it['year']}")
            print(f"      {it['url']}")
        print("\n用 --id <ID> 抓取。")
        return

    if not args.subject_id:
        ap.error("需要 --id 或 --query")

    cookie = args.cookie
    if args.cookie_file and os.path.exists(args.cookie_file):
        cookie = open(args.cookie_file, "r", encoding="utf-8").read().strip()

    m = re.match(r"\s*([\d.]+)\s*-\s*([\d.]+)\s*$", args.delay)
    delay = (float(m.group(1)), float(m.group(2))) if m else (float(args.delay), float(args.delay) + 1)

    sorts = {"hot": ("new_score",), "time": ("time",), "both": ("new_score", "time")}[args.sort]

    crawl(args.subject_id, status=args.status, sorts=sorts, max_pages=args.max_pages,
          delay=delay, cookie=cookie, out_dir=args.out, keep_html=args.keep_html)


if __name__ == "__main__":
    main()
