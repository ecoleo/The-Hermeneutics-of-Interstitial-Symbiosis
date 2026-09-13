# -*- coding: utf-8 -*-
"""
预登记词表敏感性分析（2026-09-13，配合词典归属修正）。

目的：检验核心结论对词表选择的稳健性——
  A. 微信读书：文学专业维度的 S1(点评) vs S3(想法) 层间差异，
     在删除易误命中的宽泛词条后是否依然显著；
  B. B站：幽默解构类占比区间（正文引 1.4%–8.1%）在删除宽泛词条后是否仍处低位；
     文学品质类区间（39.0%–96.7%）是否稳健。
方法：仅做删词（保守方向），不做事后加词；每组变体重算比例、Wilson CI、两比例z。
输出：data/lexicon_sensitivity.csv + 控制台摘要。
"""
import csv, json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def wilson(k, n, z=1.959964):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, (c - m) / d, (c + m) / d


def two_prop_z(k1, n1, k2, n2):
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0, 1.0
    z = (k1 / n1 - k2 / n2) / se
    pv = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, pv


# ---------------- A. 微信读书 ----------------
LEX_WR = {
    "讽刺批判/当代迁移": ["讽刺", "嘲讽", "批判", "毒舌", "吐槽", "犀利", "现实",
                    "当代", "如今", "现在", "社会", "内卷", "职场", "打工",
                    "官僚", "权力", "体制"],
    "文学专业维度": ["文体", "叙事", "油滑", "结构", "象征", "隐喻", "现代主义",
                 "现实主义", "国民性", "启蒙", "文学史", "小说技法", "语言",
                 "反讽", "荒诞", "张力", "审美", "风格"],
}
# 变体：仅删词（宽泛/易误命中词条），方向保守
VARIANTS_WR = {
    "文学专业维度": {
        "完整词表(v1.0)": None,
        "删「语言」": {"语言"},
        "删「叙事」": {"叙事"},
        "删「风格」": {"风格"},
        "删「语言+叙事+风格」": {"语言", "叙事", "风格"},
        "严格版(仅文学批评术语)": {"文体", "油滑", "象征", "隐喻", "现代主义", "现实主义",
                          "国民性", "启蒙", "文学史", "小说技法", "反讽", "荒诞", "张力", "审美"},
    },
    "讽刺批判/当代迁移": {
        "完整词表(v1.0)": None,
        "删「现实+现在」": {"现实", "现在"},
        "删「现实+现在+社会」": {"现实", "现在", "社会"},
    },
}

corpus = [json.loads(l) for l in open(
    os.path.join(DATA, "weread_corpus_40509933_2026-09-12.jsonl"), encoding="utf-8")]
S1 = [r for r in corpus if r["source"] == "S1"]
S3 = [r for r in corpus if r["source"] == "S3"]

rows = []
print("=== A. 微信读书：层间差异对词表的敏感性 ===")
for cat, variants in VARIANTS_WR.items():
    print(f"\n[{cat}]  S1(n={len(S1)}) vs S3(n={len(S3)})")
    for vname, drop in variants.items():
        words = LEX_WR[cat] if drop is None else \
            ([w for w in LEX_WR[cat] if w not in drop] if isinstance(drop, set) else list(drop))
        k1 = sum(1 for r in S1 if any(w in r["content"] for w in words))
        k3 = sum(1 for r in S3 if any(w in r["content"] for w in words))
        p1, lo1, hi1 = wilson(k1, len(S1))
        p3, lo3, hi3 = wilson(k3, len(S3))
        z, pv = two_prop_z(k1, len(S1), k3, len(S3))
        sig = "显著" if pv < 0.001 else ("边缘" if pv < 0.05 else "不显著")
        print(f"  {vname:<22} S1={p1*100:5.1f}%  S3={p3*100:4.1f}%  z={z:6.2f}  p={pv:.2e}  {sig}")
        rows.append(["微信读书", cat, vname, k1, len(S1), round(p1 * 100, 2),
                     k3, len(S3), round(p3 * 100, 2), round(z, 2), f"{pv:.2e}", sig])

# ---------------- B. B站 ----------------
LEX_BILI = {
    "幽默解构类": {"搞笑", "吐槽", "毒舌", "讽刺", "阴阳怪气", "幽默", "沙雕", "恶搞",
              "鬼畜", "整活", "爆笑", "调侃", "段子", "喜剧", "玩梗", "梗"},
    "文学品质类": {"文学", "小说", "经典", "现代文学", "名著", "读书", "人文", "文化",
              "故事新编", "周树人", "鲁迅全集", "文学经典", "现当代文学", "语文",
              "文学理论", "散文", "短篇小说"},
}
VARIANTS_BILI = {
    "幽默解构类": {
        "完整词表": None,
        "删「梗」": {"梗"},
        "删「梗+段子」": {"梗", "段子"},
    },
    "文学品质类": {
        "完整词表": None,
        "删「文化」": {"文化"},
        "删「文化+人文」": {"文化", "人文"},
    },
}
videos = []
# 与 bili_analyze.py 的 sorted(glob) 加载顺序一致（去重保留首次，顺序影响存活记录）
for fn in ["bili_故事新编.jsonl", "bili_故事新编鲁迅.jsonl", "bili_鲁迅.jsonl"]:
    videos += [json.loads(l) for l in open(
        os.path.join(DATA, "bili", fn), encoding="utf-8") if l.strip()]
# 口径对齐 bili_analyze.py：按 (bvid, 关键词) 去重保留首次（与原管线一致）
seen, dedup = set(), []
for v in videos:
    key = (v.get("bvid"), v.get("_keyword"))
    if key in seen:
        continue
    seen.add(key)
    dedup.append(v)
videos = dedup
for v in videos:
    v.setdefault("keyword", v.get("_keyword"))
    v.setdefault("order", v.get("_order"))
assert videos and all(v.get("keyword") and v.get("order") for v in videos), "字段归一化失败"

print("\n=== B. B站：占比区间对词表的敏感性（6组：3关键词×2排序）===")
print("    口径同 bili_analyze.py：标签精确匹配 + (bvid,关键词) 去重，仅变词表")
for cat, variants in VARIANTS_BILI.items():
    print(f"\n[{cat}]")
    for vname, drop in variants.items():
        words = LEX_BILI[cat] if drop is None else {w for w in LEX_BILI[cat] if w not in drop}
        vals = []
        for kw in ["故事新编 鲁迅", "故事新编", "鲁迅"]:
            for order in ["totalrank", "pubdate"]:
                sub = [v for v in videos if v.get("keyword") == kw and v.get("order") == order]
                if not sub:
                    continue
                k = sum(1 for v in sub
                        if any(t in words for t in v.get("tags", [])))
                vals.append((kw, order, len(sub), k / len(sub) * 100))
        lo = min(v[3] for v in vals)
        hi = max(v[3] for v in vals)
        print(f"  {vname:<14} 区间 {lo:5.1f}% – {hi:5.1f}%")
        for kw, order, n_, pct in vals:
            rows.append(["B站", cat, vname, kw + "|" + order, n_, round(pct, 2),
                         "", "", "", "", "", ""])

with open(os.path.join(DATA, "lexicon_sensitivity.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["平台", "类别", "词表变体", "分组/S1字段", "k或n1", "S1占比%",
                "k3", "n3", "S3占比%", "z", "p", "判读"])
    w.writerows(rows)
print("\n输出 -> data/lexicon_sensitivity.csv")
