# -*- coding: utf-8 -*-
"""
微信读书《故事新编》(bookId=40509933, 人民文学社版) "读者说"分层全量采集 v2。

通道：授权 API gateway，API key 仅从环境变量 WEREAD_API_KEY 读取，不落盘。

三个层(stratum)——预登记规则：
  S1 公开点评 /review/list（默认列表，穷尽至服务端不再给新条目；实测上限 209）
  S2 书摘类 /review/list?reviewListType=4（实测上限 26）
  S3 划线下想法 /book/readreviews：
     每内容章（跳过封面/版权页/文前辅文）先取 /book/underlines 热度表，
     按划线人数 count 取前 3 个 range（count>0），每 range 取第 1 页 count=10。
  S4 章节热门划线 /book/bestbookmarks（每内容章一次，含被划原文，供划线主题编码）

匿名化：剔除 author / userVid / avatar / reviewId，仅留文本与行为指标。
采样性质（须写入方法论）：排序均为平台默认（热度/推荐混合），非时间序、非随机；
  未公开、被删除、仅划线未留文字者不在框内；S3 每 range 仅第 1 页（约10条），
  属"高热 range 的前排想法"，推论不可外推至全书全部想法。
"""
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data")
BOOK_ID = "40509933"
SKIP_TITLES = {"封面", "版权页", "文前辅文"}
TOP_RANGES_PER_CH = 3
IDEAS_PER_RANGE = 10


def gw(key, body):
    body["skill_version"] = "1.0.3"
    req = urllib.request.Request(
        "https://i.weread.qq.com/api/agent/gateway",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "weread-skill/1.0.3"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def safe_int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def main():
    key = os.environ.get("WEREAD_API_KEY", "").strip()
    if not key:
        print("FATAL: WEREAD_API_KEY 未设置"); sys.exit(2)

    log = open(os.path.join(OUT_DIR, "weread_collect.log"), "w", encoding="utf-8")
    def w(msg):
        print(msg); log.write(msg + "\n"); log.flush()

    seen = set()
    corpus = []          # 用户生成文本（点评+想法）
    bookmarks = []       # 被划原文（热门划线）
    stats = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}

    # ---------- S1/S2: /review/list ----------
    for lt in (None, 4):
        tag = "S1" if lt is None else "S2"
        for m in range(0, 400, 20):
            body = {"api_name": "/review/list", "bookId": BOOK_ID,
                    "count": 20, "maxIdx": m}
            if lt:
                body["reviewListType"] = lt
            try:
                d = gw(key, body)
            except Exception as e:
                w(f"{tag} maxIdx={m} ERR {type(e).__name__} -> 停止本层"); break
            rvs = d.get("reviews") or []
            new = 0
            for x in rvs:
                slot = x.get("review") or {}
                rid = slot.get("reviewId")
                if not rid or rid in seen:
                    continue
                inner = slot.get("review") or {}
                corpus.append({
                    "source": tag,
                    "chapter": inner.get("chapterName") or "",
                    "content": (inner.get("content") or "").strip(),
                    "createTime": safe_int(inner.get("createTime")),
                    "likesCount": safe_int(slot.get("likesCount")),
                    "commentsCount": safe_int(slot.get("commentsCount")),
                })
                seen.add(rid); new += 1
            stats[tag] += new
            w(f"{tag} maxIdx={m} 本页={len(rvs)} 新增={new} 层累计={stats[tag]}")
            if not rvs or new == 0:
                break
            time.sleep(1.2)

    # ---------- 章节目录 ----------
    d = gw(key, {"api_name": "/book/chapterinfo", "bookId": BOOK_ID})
    chapters = [c for c in (d.get("chapters") or [])
                if c.get("title") not in SKIP_TITLES]
    w(f"内容章: {len(chapters)}")

    # ---------- S3/S4: 逐章 ----------
    for c in chapters:
        cu, title = c.get("chapterUid"), c.get("title")
        # S4 章节热门划线
        try:
            bb = gw(key, {"api_name": "/book/bestbookmarks",
                          "bookId": BOOK_ID, "chapterUid": cu})
            for it in (bb.get("items") or []):
                text = ((it.get("markText") or it.get("content") or "")).strip()
                if not text:
                    continue
                bookmarks.append({
                    "chapter": title,
                    "markText": text,
                    "totalCount": safe_int(it.get("totalCount")),
                })
                stats["S4"] += 1
        except Exception as e:
            w(f"S4 {title} ERR {type(e).__name__}")
        time.sleep(1.0)

        # S3 划线下想法
        try:
            u = gw(key, {"api_name": "/book/underlines",
                         "bookId": BOOK_ID, "chapterUid": cu})
        except Exception as e:
            w(f"S3-underlines {title} ERR {type(e).__name__}"); continue
        uls = [x for x in (u.get("underlines") or []) if safe_int(x.get("count")) > 0]
        uls.sort(key=lambda x: safe_int(x.get("count")), reverse=True)
        top = uls[:TOP_RANGES_PER_CH]
        time.sleep(1.0)
        for x in top:
            rng = x.get("range")
            if not rng:
                continue
            try:
                rr = gw(key, {"api_name": "/book/readreviews",
                              "bookId": BOOK_ID, "chapterUid": cu,
                              "reviews": [{"range": rng, "maxIdx": 0,
                                           "count": IDEAS_PER_RANGE}]})
            except Exception as e:
                w(f"S3 {title} range={rng} ERR {type(e).__name__}"); continue
            for blk in (rr.get("reviews") or []):
                for rv in (blk.get("pageReviews") or []):
                    rid = rv.get("reviewId")
                    if not rid or rid in seen:
                        continue
                    inner = rv.get("review") or {}
                    content = (inner.get("content") or
                               inner.get("abstract") or "").strip()
                    if not content:
                        continue
                    corpus.append({
                        "source": "S3",
                        "chapter": inner.get("chapterName") or title,
                        "content": content,
                        "createTime": safe_int(inner.get("createTime")),
                        "likesCount": safe_int(rv.get("likesCount")),
                        "commentsCount": safe_int(rv.get("commentsCount")),
                    })
                    seen.add(rid); stats["S3"] += 1
            time.sleep(1.2)
        w(f"章 {title}: S3累计={stats['S3']} S4累计={stats['S4']}")

    # ---------- 落盘 ----------
    stamp = time.strftime("%Y-%m-%d")
    f1 = os.path.join(OUT_DIR, f"weread_corpus_40509933_{stamp}.jsonl")
    with open(f1, "w", encoding="utf-8") as f:
        for rec in corpus:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    f2 = os.path.join(OUT_DIR, f"weread_bookmarks_40509933_{stamp}.jsonl")
    with open(f2, "w", encoding="utf-8") as f:
        for rec in bookmarks:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    meta = {
        "bookId": BOOK_ID, "edition": "人民文学出版社版",
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_generated_total": len(corpus),
        "strata": stats,
        "bookmarks_total": len(bookmarks),
        "server_reviewsCnt": 547,
        "preregistered_rules": {
            "S1": "/review/list 默认列表穷尽（服务端实际上限209/547）",
            "S2": "/review/list reviewListType=4 穷尽（上限26）",
            "S3": "每内容章 underlines 按划线人数取前3 range，每range第1页10条",
            "S4": "每内容章 bestbookmarks 全量返回",
        },
        "anonymized": True,
        "sampling_note": ("平台默认排序（热度/推荐混合），非时间序非随机；"
                          "未公开/被删/仅划线无文字者不在框内；"
                          "S3为高热range的前排想法，不可外推至全部想法。"),
    }
    with open(os.path.join(OUT_DIR, f"weread_corpus_40509933_{stamp}_meta.json"),
              "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    w(f"DONE corpus={len(corpus)} (S1={stats['S1']} S2={stats['S2']} S3={stats['S3']}) "
      f"bookmarks={len(bookmarks)} -> {f1}")
    log.close()


if __name__ == "__main__":
    main()
