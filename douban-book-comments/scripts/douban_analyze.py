#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
douban_analyze.py — 豆瓣短评量化分析器

输入 douban_fetch.py 产出的 JSONL（+ meta.json），输出若干 CSV 与 stats.json。
依赖尽量可选：无 jieba/pandas/numpy/sklearn 时会自动降级为纯 Python 实现。

用法
----
  python douban_analyze.py --input ./douban_data/comments_2046909_P.jsonl --out ./douban_data
  python douban_analyze.py --input ... --sentiment snownlp --topk 40

产出
----
  stats.json                     总体指标 + 覆盖率 + 方法论声明
  rating_distribution.csv        1-5 星分布（含无评分）
  rating_title_distribution.csv  力荐/推荐/还行/较差/很差 分布
  yearly_trend.csv               逐年：评论数、均分、平均长度、高赞票数
  length_distribution.csv        文本长度分桶
  keywords_top.csv               全样本高频关键词（TF-IDF 加权）
  keywords_by_rating.csv         高分(4-5星) vs 低分(1-2星) 特征词对比
  top_comments.csv               高赞短评 Top N
  yearly_keywords.csv            分时段关键词（接受史漂移，时段可选）
  sentiment_rating_cross.csv     情感启发式 × 星级 交叉表（--sentiment 非 off 时）
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- 可选依赖
try:
    import jieba  # noqa
    HAS_JIEBA = True
except Exception:
    HAS_JIEBA = False
try:
    import numpy as np  # noqa
    HAS_NUMPY = True
except Exception:
    HAS_NUMPY = False

STOPWORDS = set("""
的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这
但是 还是 这个 那个 什么 因为 所以 如果 可以 就是 觉得 感觉 真的 非常 特别 已经 还有 以及
而且 只是 不过 其 之 与 而 或 等 更 再 又 让 给 把 被 从 对 向 里 后 前 中 下 上 我们 他们
它 他 她 吧 啊 呢 吗 嗯 哦 呀 啦 嘛 一本 这本 这本 书 读 看过 看完 看了 读了 这本 本书
一个 一些 这样 那样 一样 一点 有点 有的 所有 一些 任何 每个 很多 太多 不少 第二 第三
""".split())

PUNCT = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]+")

POS_LEX = set("好看 精彩 喜欢 经典 神作 优秀 深刻 精彩 有趣 幽默 犀利 震撼 感动 推荐 满分 精彩绝伦 爱 杰作 伟大 完美 惊艳 畅快 恰切 精妙 精彩 值得 迷 神 强 牛 棒 佳 妙 绝".split())
NEG_LEX = set("无聊 烂 差 失望 狗屁 垃圾 看不懂 糟糕 讨厌 无趣 平庸 一般 凑合 敷衍 拖沓 乏味 空洞 浪费 后悔 弃 难看 莫名其妙 矫情 做作 差劲 不值 太差 读不下去".split())


# ---------------------------------------------------------------- 工具
def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xa, ya = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = mean(xa), mean(ya)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    dx = math.sqrt(sum((a - mx) ** 2 for a in xa))
    dy = math.sqrt(sum((b - my) ** 2 for b in ya))
    return num / (dx * dy) if dx and dy else None


def shannon_entropy_normalized(counter):
    tot = sum(counter.values())
    if tot == 0:
        return None
    h = -sum((c / tot) * math.log(c / tot, 2) for c in counter.values() if c)
    return h / math.log(len(counter), 2) if len(counter) > 1 else 0.0


def year_of(t):
    m = re.match(r"(\d{4})", t or "")
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- 分词与关键词
def tokenize(text):
    text = PUNCT.sub(" ", text)
    if HAS_JIEBA:
        import jieba
        toks = [t.strip() for t in jieba.cut(text) if t.strip()]
    else:
        # 降级：切分为单字，n-gram 层再做组合（见 ngram_keywords）
        toks = [ch for ch in text if ch.strip()]
    return [t for t in toks if t not in STOPWORDS and len(t) > 0]


def ngram_keywords(texts, topk=40, min_freq=4, max_n=4, cohesion_th=2.5):
    """无 jieba 时的降级新词发现：字符 n-gram + 点互信息凝聚度剪枝。"""
    from itertools import combinations
    freq = Counter()
    uni = Counter()
    for t in texts:
        s = PUNCT.sub("", t)
        uni.update(s)
        for n in range(2, max_n + 1):
            for i in range(len(s) - n + 1):
                freq[s[i:i + n]] += 1
    N = sum(uni.values())
    scored = {}
    for g, f in freq.items():
        if f < min_freq or len(g) < 2:
            continue
        if g in STOPWORDS or all(ch in STOPWORDS for ch in g):
            continue
        # 凝聚度：所有二分切分中 PMI 的最小值
        best = float("inf")
        for k in range(1, len(g)):
            a, b = g[:k], g[k:]
            pa, pb, pab = uni[a] / N, uni[b] / N, f / N
            expected = freq.get(a, 0) * freq.get(b, 0)
            if expected == 0:
                best = 0
                break
            pmi = math.log((pab * N) / (pa * pb * N)) if pa * pb > 0 else 0
            pmi = math.log(f * N / (freq.get(a, 0) * freq.get(b, 0)))
            best = min(best, pmi)
        if best is None or best < cohesion_th:
            continue
        scored[g] = (f, round(best, 3))
    # 剪枝：若某串的频次与包含它的更长串相同，说明它不独立成词
    kept = dict(scored)
    for g in list(kept):
        for n in range(len(g) + 1, max_n + 1):
            for longer in [x for x in scored if len(x) == n and g in x]:
                if scored[longer][0] >= freq[g] * 0.9:
                    kept.pop(g, None)
                    break
            else:
                continue
            break
    out = sorted(kept.items(), key=lambda kv: kv[1][0] * kv[1][1], reverse=True)[:topk]
    return [(g, v[0]) for g, v in out]


def tfidf_keywords(docs, topk=40, min_df=2):
    """手写 TF-IDF（语料 = 每条短评一篇文档）。"""
    df = Counter()
    tok_docs = []
    for d in docs:
        toks = tokenize(d)
        tok_docs.append(toks)
        df.update(set(toks))
    N = len(tok_docs)
    tf_all = Counter()
    weight = defaultdict(float)
    for toks in tok_docs:
        tf = Counter(toks)
        for w, c in tf.items():
            if df[w] < min_df or len(w) < 2 and not HAS_JIEBA:
                continue
            tf_all[w] += c
            weight[w] += (1 + math.log(c)) * math.log(N / (1 + df[w]))
    ranked = sorted(weight.items(), key=lambda kv: kv[1], reverse=True)[:topk]
    return [(w, tf_all[w], round(s, 3)) for w, s in ranked]


def lexicon_sentiment(text):
    toks = set(tokenize(text))
    if not HAS_JIEBA:
        toks = set([text[i:i + 2] for i in range(len(text) - 1)] + list(text))
    p = len(toks & POS_LEX)
    n = len(toks & NEG_LEX)
    if p == n == 0:
        return "中性", 0.0
    score = (p - n) / (p + n)
    return ("正面" if score > 0 else "负面"), round(score, 3)


# ---------------------------------------------------------------- 主分析
def analyze(rows, meta=None, topk=40, sentiment="off", period="year"):
    n_all = len(rows)
    rated = [r for r in rows if r.get("rating")]
    ratings = [r["rating"] for r in rated]
    texts = [r.get("text", "") for r in rows]
    lens = [len(t) for t in texts]
    votes = [r.get("votes", 0) or 0 for r in rows]
    years = [year_of(r.get("time")) for r in rows]

    # 评分分布
    rc = Counter(ratings)
    rating_dist = [[s, rc.get(s, 0),
                    round(rc.get(s, 0) / len(ratings) * 100, 2) if ratings else 0]
                   for s in range(1, 6)]
    rating_dist.append([0, n_all - len(rated),
                        round((n_all - len(rated)) / n_all * 100, 2) if n_all else 0])

    tc = Counter(r.get("rating_title", "") or "(无)" for r in rows)
    title_dist = [[k, v] for k, v in tc.most_common()]

    # 时间趋势
    ymap = defaultdict(list)
    for r, y in zip(rows, years):
        if y:
            ymap[y].append(r)
    yearly = []
    for y in sorted(ymap):
        rs = ymap[y]
        yr = [x["rating"] for x in rs if x.get("rating")]
        yearly.append([y, len(rs),
                       round(mean(yr), 3) if yr else "",
                       round(mean([len(x.get("text", "")) for x in rs]), 1),
                       round(mean([x.get("votes", 0) or 0 for x in rs]), 1)])

    # 长度分桶
    buckets = [(0, 10), (11, 30), (31, 60), (61, 120), (121, 300), (301, 10 ** 6)]
    len_dist = []
    for lo, hi in buckets:
        c = sum(1 for l in lens if lo <= l <= hi)
        len_dist.append([f"{lo}-{hi if hi < 10**6 else '+'}", c,
                         round(c / n_all * 100, 2) if n_all else 0])

    # 关键词
    if HAS_JIEBA:
        kw = tfidf_keywords(texts, topk=topk)
        kw_rows = [[w, c, s] for w, c, s in kw]
        tok_method = "jieba + TF-IDF"
    else:
        kw = ngram_keywords(texts, topk=topk)
        kw_rows = [[w, c, ""] for w, c in kw]
        tok_method = "字符n-gram + PMI（jieba 未安装，降级）"

    # 高分 vs 低分 特征词
    high = [r.get("text", "") for r in rows if (r.get("rating") or 0) >= 4]
    low = [r.get("text", "") for r in rows if (r.get("rating") or 0) <= 2]
    def feat(docs, exclude, k=20):
        if not docs or HAS_JIEBA is False:
            return []
        out = []
        for w, c, s in tfidf_keywords(docs, topk=k * 3):
            if w in exclude:
                continue
            out.append((w, c))
            if len(out) >= k:
                break
        return out
    if HAS_JIEBA:
        hf = feat(high, set(), 20)
        lf = feat(low, set(w for w, _ in hf), 20)
    else:
        hf = ngram_keywords(high, topk=20) if high else []
        lf = ngram_keywords(low, topk=20) if low else []
    rating_kw = []
    for i in range(max(len(hf), len(lf))):
        rating_kw.append([
            hf[i][0] if i < len(hf) else "", hf[i][1] if i < len(hf) else "",
            lf[i][0] if i < len(lf) else "", lf[i][1] if i < len(lf) else "",
        ])

    # 分时段关键词（接受史漂移）
    yk = []
    if HAS_JIEBA and len(ymap) >= 2:
        ys = sorted(ymap)
        # 等分为 4 段（不足 4 年则按年）
        seg = max(1, math.ceil(len(ys) / 4))
        for i in range(0, len(ys), seg):
            chunk = ys[i:i + seg]
            docs = [r.get("text", "") for y in chunk for r in ymap[y]]
            ks = tfidf_keywords(docs, topk=15)
            yk.append([f"{chunk[0]}-{chunk[-1]}", len(docs),
                       " / ".join(w for w, _, _ in ks)])
    elif not HAS_JIEBA:
        yk = [["(需安装 jieba 以启用分时段关键词)", "", ""]]

    # 高赞短评
    tops = sorted(rows, key=lambda r: r.get("votes", 0) or 0, reverse=True)[:30]
    top_rows = [[r.get("votes", 0), r.get("rating") or "", r.get("time", ""),
                 r.get("user", ""), (r.get("text", "") or "").replace("\n", " ")[:200]]
                for r in tops]

    # 情感
    sent_rows = []
    if sentiment != "off":
        cross = defaultdict(Counter)
        for r in rows:
            if sentiment == "snownlp":
                try:
                    from snownlp import SnowNLP
                    s = SnowNLP(r.get("text", "")).sentiments
                    lab = "正面" if s >= 0.6 else ("负面" if s < 0.4 else "中性")
                except Exception:
                    lab, s = lexicon_sentiment(r.get("text", ""))
            else:
                lab, s = lexicon_sentiment(r.get("text", ""))
            cross[r.get("rating") or 0][lab] += 1
        for star in sorted(cross):
            c = cross[star]
            tot = sum(c.values())
            sent_rows.append([star, c.get("正面", 0), c.get("中性", 0), c.get("负面", 0), tot])

    # 汇总
    stats = {
        "book": (meta or {}).get("book_title", ""),
        "subject_id": (meta or {}).get("subject_id", ""),
        "status_label": (meta or {}).get("status_label", ""),
        "n_comments": n_all,
        "n_rated": len(rated),
        "declared_total": (meta or {}).get("declared_total"),
        "coverage": (meta or {}).get("coverage"),
        "logged_in": (meta or {}).get("logged_in", False),
        "rating_mean": round(mean(ratings), 3) if ratings else None,
        "rating_median": median(ratings),
        "rating_stdev": round(stdev(ratings), 3) if ratings else None,
        "rating_polarization_entropy": round(shannon_entropy_normalized(rc), 4) if rc else None,
        "pct_5star": round(rc.get(5, 0) / len(ratings) * 100, 2) if ratings else None,
        "pct_low_1_2star": round((rc.get(1, 0) + rc.get(2, 0)) / len(ratings) * 100, 2) if ratings else None,
        "text_len_mean": round(mean(lens), 1) if lens else None,
        "text_len_median": median(lens),
        "votes_mean": round(mean(votes), 1) if votes else None,
        "votes_max": max(votes) if votes else None,
        "year_min": min([y for y in years if y], default=None),
        "year_max": max([y for y in years if y], default=None),
        "corr_len_rating": round(pearson(
            [len(r.get("text", "")) for r in rated], ratings), 3) if len(rated) > 3 else None,
        "corr_votes_rating": round(pearson(
            [r.get("votes", 0) or 0 for r in rated], ratings), 3) if len(rated) > 3 else None,
        "tokenizer": tok_method,
        "sentiment_method": sentiment,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "caveat": "覆盖率为抓取数/页面声明总数；豆瓣未登录态通常仅可达前 ~180 条，"
                  "样本非随机（热门排序偏向高赞），统计推断需谨慎。",
    }

    return {
        "stats": stats,
        "rating_distribution": (["星级", "条数", "占比%"], rating_dist),
        "rating_title_distribution": (["评价标签", "条数"], title_dist),
        "yearly_trend": (["年份", "评论数", "均分", "平均字数", "平均有用数"], yearly),
        "length_distribution": (["字数区间", "条数", "占比%"], len_dist),
        "keywords_top": (["关键词", "词频", "TF-IDF权重"], kw_rows),
        "keywords_by_rating": (["高分特征词", "词频", "低分特征词", "词频"], rating_kw),
        "yearly_keywords": (["时段", "评论数", "Top关键词"], yk),
        "top_comments": (["有用数", "星级", "时间", "用户", "短评"], top_rows),
        "sentiment_rating_cross": (["星级", "正面", "中性", "负面", "合计"], sent_rows),
    }


def main():
    ap = argparse.ArgumentParser(description="豆瓣短评量化分析")
    ap.add_argument("--input", required=True, help="comments_*.jsonl 路径")
    ap.add_argument("--meta", default="", help="meta_*.json 路径（默认与 input 同目录推断）")
    ap.add_argument("--out", default="", help="输出目录（默认与 input 同目录）")
    ap.add_argument("--topk", type=int, default=40)
    ap.add_argument("--sentiment", default="off", choices=["off", "lexicon", "snownlp"])
    args = ap.parse_args()

    rows = load_jsonl(args.input)
    if not rows:
        print("没有数据，退出。")
        return
    out_dir = args.out or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(out_dir, exist_ok=True)

    meta_path = args.meta
    if not meta_path:
        base = os.path.basename(args.input)
        m = re.search(r"comments_(\d+)_([A-Z])\.jsonl", base)
        if m:
            meta_path = os.path.join(out_dir, f"meta_{m.group(1)}_{m.group(2)}.json")
    meta = {}
    if meta_path and os.path.exists(meta_path):
        meta = json.load(open(meta_path, "r", encoding="utf-8"))

    res = analyze(rows, meta, topk=args.topk, sentiment=args.sentiment)

    name_map = {
        "rating_distribution": "rating_distribution.csv",
        "rating_title_distribution": "rating_title_distribution.csv",
        "yearly_trend": "yearly_trend.csv",
        "length_distribution": "length_distribution.csv",
        "keywords_top": "keywords_top.csv",
        "keywords_by_rating": "keywords_by_rating.csv",
        "yearly_keywords": "yearly_keywords.csv",
        "top_comments": "top_comments.csv",
    }
    for key, fn in name_map.items():
        header, data = res[key]
        write_csv(os.path.join(out_dir, fn), header, data)
    if args.sentiment != "off":
        h, d = res["sentiment_rating_cross"]
        write_csv(os.path.join(out_dir, "sentiment_rating_cross.csv"), h, d)

    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(res["stats"], f, ensure_ascii=False, indent=2)

    s = res["stats"]
    print("\n========== 分析完成 ==========")
    print(f"条目         : {s['book']} (#{s['subject_id']}) / {s['status_label']}")
    print(f"样本量       : {s['n_comments']} 条（有评分 {s['n_rated']} 条）")
    if s["coverage"]:
        print(f"覆盖率       : {s['coverage']*100:.2f}%  (声明总数 {s['declared_total']})")
    print(f"均分         : {s['rating_mean']} ± {s['rating_stdev']}（中位 {s['rating_median']}）")
    print(f"五星占比     : {s['pct_5star']}%   低分(1-2星)占比 {s['pct_low_1_2star']}%")
    print(f"极化度(熵)   : {s['rating_polarization_entropy']}")
    print(f"平均字数     : {s['text_len_mean']}   平均有用数 {s['votes_mean']}")
    print(f"年份跨度     : {s['year_min']} – {s['year_max']}")
    print(f"字数×评分 r  : {s['corr_len_rating']}   有用数×评分 r {s['corr_votes_rating']}")
    print(f"分词方法     : {s['tokenizer']}")
    print(f"输出目录     : {out_dir}")


if __name__ == "__main__":
    main()
