# -*- coding: utf-8 -*-
"""
微信读书语料正式主题编码（预登记词典 v1.0，冻结于 2026-09-12）。

词典说明（预登记纪律）：
- 类别与词表在正式计数前冻结，写入本文件与复现说明；
- 词表源自 2026-09-12 上午的探索性扫描，正式计数未再增删词条；
- 多重命中允许（一条文本可命中多个类别），比例分母为层内文本数；
- 本编码为词典法（dictionary-based），属词元级代理测量，
  结论表述须限定为"词典命中比例"，不得表述为人工主题编码结论。

输入：data/weread_corpus_40509933_2026-09-12.jsonl
     data/weread_bookmarks_40509933_2026-09-12.jsonl
输出：data/weread_coding_by_stratum.csv
     data/weread_bookmarks_pianmu.csv
     data/weread_bookmarks_top.csv
     data/weread_coding_summary.json
"""
import json, math, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STAMP = "2026-09-12"

# ---------- 预登记词典 v1.0 ----------
LEX = {
    "讽刺批判/当代迁移": ["讽刺", "嘲讽", "批判", "毒舌", "吐槽", "犀利", "现实",
                    "当代", "如今", "现在", "社会", "内卷", "职场", "打工",
                    "官僚", "权力", "体制"],
    "情感共鸣/个人经验": ["喜欢", "感动", "心疼", "可爱", "悲哀", "难过", "泪",
                    "笑", "哈哈", "共鸣", "震撼", "佩服", "羡慕", "孤独",
                    "无奈", "心酸"],
    "文学专业维度": ["文体", "叙事", "油滑", "结构", "象征", "隐喻", "现代主义",
                 "现实主义", "国民性", "启蒙", "文学史", "小说技法", "语言",
                 "反讽", "荒诞", "张力", "审美", "风格"],
    "篇目/人物指涉": ["铸剑", "理水", "奔月", "补天", "采薇", "出关", "非攻", "起死",
                 "眉间尺", "后羿", "大禹", "女娲", "老子", "伯夷", "叔齐",
                 "嫦娥", "墨子", "庄子"],
}

# 篇目归属：章标题序列中，"[1]"标记新篇目起始，其后的"二/三/…"归属该篇目
def pianmu_of(chapter_title, state):
    t = chapter_title or ""
    if t.endswith("[1]"):
        state["cur"] = t[:-3]
    elif t == "序言":
        state["cur"] = "序言"
    return state["cur"]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - m) / d, (c + m) / d)


def main():
    corpus = [json.loads(l) for l in open(
        os.path.join(DATA, f"weread_corpus_40509933_{STAMP}.jsonl"), encoding="utf-8")]
    bms = [json.loads(l) for l in open(
        os.path.join(DATA, f"weread_bookmarks_40509933_{STAMP}.jsonl"), encoding="utf-8")]

    # ---------- 语料编码 ----------
    rows = []
    summary = {"N": len(corpus), "lexicon_version": "v1.0", "strata": {}}
    for src in ("S1", "S3"):
        sub = [r for r in corpus if r["source"] == src]
        n = len(sub)
        summary["strata"][src] = {"n": n, "cats": {}}
        for cat, words in LEX.items():
            k = sum(1 for r in sub if any(w in r["content"] for w in words))
            p, lo, hi = wilson(k, n)
            summary["strata"][src]["cats"][cat] = {
                "k": k, "p": round(p, 4),
                "ci95": [round(lo, 4), round(hi, 4)]}
            rows.append([src, cat, k, n, round(p, 4), round(lo, 4), round(hi, 4)])
    with open(os.path.join(DATA, "weread_coding_by_stratum.csv"), "w", encoding="utf-8-sig") as f:
        f.write("stratum,category,k,n,proportion,ci95_low,ci95_high\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    # 语料篇目分布（S3，依采集顺序的位置映射）
    st = {"cur": "未定位"}
    pm = Counter()
    for r in corpus:
        if r["source"] != "S3":
            continue
        pm[pianmu_of(r["chapter"], st)] += 1
    summary["S3_by_pianmu"] = dict(pm.most_common())

    # ---------- 热门划线 ----------
    st = {"cur": "未定位"}
    bm_pm = Counter()
    for b in bms:
        bm_pm[pianmu_of(b["chapter"], st)] += 1
    summary["bookmarks_by_pianmu_count"] = dict(bm_pm.most_common())
    with open(os.path.join(DATA, "weread_bookmarks_pianmu.csv"), "w", encoding="utf-8-sig") as f:
        f.write("pianmu,n_bookmarks,total_mark_persons\n")
        persons = Counter()
        st = {"cur": "未定位"}
        for b in bms:
            persons[pianmu_of(b["chapter"], st)] += b.get("totalCount") or 0
        for pmu, n_ in bm_pm.most_common():
            f.write(f"{pmu},{n_},{persons[pmu]}\n")
    # 先在文件原始顺序上完成篇目映射，再排序取TOP（位置映射不可用于打乱后的序列）
    st = {"cur": "未定位"}
    for b in bms:
        b["_pianmu"] = pianmu_of(b["chapter"], st)
    top = sorted(bms, key=lambda b: -(b.get("totalCount") or 0))[:15]
    with open(os.path.join(DATA, "weread_bookmarks_top.csv"), "w", encoding="utf-8-sig") as f:
        f.write("rank,pianmu,mark_persons,markText\n")
        for i, b in enumerate(top, 1):
            txt = b["markText"].replace(",", "，").replace("\n", " ")[:60]
            f.write(f"{i},{b['_pianmu']},{b.get('totalCount')},{txt}\n")

    with open(os.path.join(DATA, "weread_coding_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary["strata"], ensure_ascii=False, indent=1))
    print("S3篇目:", summary["S3_by_pianmu"])
    print("划线篇目:", summary["bookmarks_by_pianmu_count"])
    print("TOP5划线:", [(b.get("totalCount"), b["markText"][:24]) for b in top[:5]])


if __name__ == "__main__":
    main()
