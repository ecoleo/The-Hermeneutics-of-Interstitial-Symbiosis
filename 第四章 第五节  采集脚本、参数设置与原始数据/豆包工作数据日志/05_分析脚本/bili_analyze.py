#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站《故事新编》视频标签与标题的统计分析（纯标准库）

科学性与有效性保障：
1. 标签分类词典【预先登记】(pre-registered)，在分析前固定，不随结果调整，避免事后挑选。
2. 所有比例给出 Wilson 95% 置信区间，而非仅报点估计。
3. 组间差异（综合排序 vs 最新排序、跨关键词）用两比例 z 检验，报告 z 与 p。
4. 标题耸动度为【启发式指标】，必须与播放量等可核验行为指标交叉验证后方可解读，
   不得单独作为结论（与 SnowNLP 情感分同等纪律）。

用法: python bili_analyze.py --data-dir <dir> --out <dir>
"""
import argparse
import csv
import glob
import json
import math
import os
from collections import Counter

# ---------------- 预先登记的标签分类词典（分析前固定） ----------------
LEX = {
    "幽默解构类": {"搞笑", "吐槽", "毒舌", "讽刺", "阴阳怪气", "幽默", "沙雕", "恶搞",
                   "鬼畜", "整活", "爆笑", "调侃", "段子", "喜剧", "玩梗", "梗"},
    "文学品质类": {"文学", "小说", "经典", "现代文学", "名著", "读书", "人文", "文化",
                   "故事新编", "周树人", "鲁迅全集", "文学经典", "现当代文学", "语文",
                   "文学理论", "散文", "短篇小说"},
    "知识教育类": {"知识", "科普", "教育", "学习", "课程", "讲解", "解读", "考试",
                   "高考", "语文课", "历史", "哲学", "思想", "学术", "大学", "课堂"},
    "有声说书类": {"有声小说", "有声书", "说书", "朗读", "听书", "配音", "播讲", "演播"},
}

# 标题耸动度标记词（预先登记，启发式）
SENS_MARKERS = ["！", "!", "狠狠", "简直", "竟然", "居然", "别再", "绝了", "炸了",
                "震惊", "可怕", "离谱", "逆天", "疯狂", "揭秘", "真相", "凭什么",
                "太", "爆", "怒", "离大谱", "万万没想到", "细思极恐"]


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def wilson_ci(x, n, z=1.96):
    """Wilson  score 区间：小样本/极端比例下比正态近似稳健。"""
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def two_prop_z(x1, n1, x2, n2):
    """两比例 z 检验（合并方差），返回 (z, 双尾p)。"""
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p1 - p2) / se
    return (z, 2 * (1 - norm_cdf(abs(z))))


def spearman(xs, ys):
    """Spearman 秩相关 + 正态近似显著性（n>30 可用）。"""
    n = len(xs)
    if n < 8:
        return (float("nan"), float("nan"))

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return (float("nan"), float("nan"))
    rho = num / (dx * dy)
    z = rho * math.sqrt(n - 1)
    return (rho, 2 * (1 - norm_cdf(abs(z))))


def has_any(lex, tags):
    return any(t in lex for t in tags)


def sens_score(title):
    t = title or ""
    return sum(1 for m in SENS_MARKERS if m in t)


def load(data_dir):
    rows = []
    for f in sorted(glob.glob(os.path.join(data_dir, "bili_*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    # 同一 bvid 可能出现在多个关键词下，保留首次并按 (bvid,keyword) 去重
    seen, out = set(), []
    for r in rows:
        key = (r.get("bvid"), r.get("_keyword"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows = load(args.data_dir)
    print(f"载入样本: {len(rows)} 条（按 bvid×关键词 去重后）")
    kws = sorted({r.get("_keyword") for r in rows if r.get("_keyword")})
    print("关键词组:", kws)

    # ---------- 1. 分类占比（含 Wilson CI） ----------
    res = []
    for kw in kws:
        for order in ("totalrank", "pubdate"):
            sub = [r for r in rows if r.get("_keyword") == kw and r.get("_order") == order]
            n = len(sub)
            if not n:
                continue
            for cat, lex in LEX.items():
                x = sum(1 for r in sub if has_any(lex, r.get("tags", [])))
                lo, hi = wilson_ci(x, n)
                res.append({
                    "关键词": kw, "排序": order, "样本量": n,
                    "类别": cat, "命中数": x, "占比%": round(x / n * 100, 2),
                    "CI下限%": round(lo * 100, 2), "CI上限%": round(hi * 100, 2),
                })
    with open(os.path.join(args.out, "bili_category_stats.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader()
        w.writerows(res)

    print("\n=== 各类别占比（Wilson 95% CI）===")
    for kw in kws:
        for order, lab in (("totalrank", "综合"), ("pubdate", "最新")):
            sub = [r for r in rows if r.get("_keyword") == kw and r.get("_order") == order]
            if not sub:
                continue
            n = len(sub)
            parts = []
            for cat, lex in LEX.items():
                x = sum(1 for r in sub if has_any(lex, r.get("tags", [])))
                lo, hi = wilson_ci(x, n)
                parts.append(f"{cat}={x/n*100:.1f}%[{lo*100:.1f},{hi*100:.1f}]")
            print(f"  {kw} / {lab} (n={n}): " + "  ".join(parts))

    # ---------- 2. 综合 vs 最新 显著性检验 ----------
    print("\n=== 综合排序 vs 最新排序（两比例 z 检验）===")
    tests = []
    for kw in kws:
        for cat, lex in LEX.items():
            a = [r for r in rows if r.get("_keyword") == kw and r.get("_order") == "totalrank"]
            b = [r for r in rows if r.get("_keyword") == kw and r.get("_order") == "pubdate"]
            if not a or not b:
                continue
            x1 = sum(1 for r in a if has_any(lex, r.get("tags", [])))
            x2 = sum(1 for r in b if has_any(lex, r.get("tags", [])))
            z, p = two_prop_z(x1, len(a), x2, len(b))
            sig = "显著" if p < 0.05 else "不显著"
            tests.append({"关键词": kw, "类别": cat, "z": round(z, 3),
                          "p": round(p, 4), "判读": sig})
            print(f"  {kw} / {cat}: 综合 {x1/len(a)*100:.1f}% vs 最新 {x2/len(b)*100:.1f}%  "
                  f"z={z:+.2f}, p={p:.4f} → {sig}")
    with open(os.path.join(args.out, "bili_order_tests.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tests[0].keys()))
        w.writeheader()
        w.writerows(tests)

    # ---------- 3. 标题耸动度 vs 播放量（启发式，须交叉验证） ----------
    print("\n=== 标题耸动度 × 播放量（Spearman；启发式指标，仅作辅助）===")
    valid = [r for r in rows if (r.get("play") or 0) > 0 and r.get("title")]
    if len(valid) >= 30:
        xs = [sens_score(r["title"]) for r in valid]
        ys = [math.log10((r["play"] or 0) + 1) for r in valid]
        rho, p = spearman(xs, ys)
        print(f"  n={len(valid)}  Spearman rho={rho:+.3f}, p={p:.4f} "
              f"({'显著' if p < 0.05 else '不显著'})")
        hi = [r for r in valid if sens_score(r["title"]) >= 2]
        lo = [r for r in valid if sens_score(r["title"]) == 0]
        if hi and lo:
            mh = sum(r["play"] for r in hi) / len(hi)
            ml = sum(r["play"] for r in lo) / len(lo)
            print(f"  耸动标题(≥2标记) n={len(hi)} 平均播放={mh:,.0f}")
            print(f"  平实标题(0标记) n={len(lo)} 平均播放={ml:,.0f}")
            print(f"  倍数={mh/ml:.2f}x")
    else:
        print("  有效样本不足 30，跳过。")

    # ---------- 4. 高频标签 ----------
    print("\n=== 高频标签 Top20（全样本）===")
    c = Counter(t for r in rows for t in r.get("tags", []))
    print("  " + ", ".join(f"{t}:{n}" for t, n in c.most_common(20)))
    with open(os.path.join(args.out, "bili_tags_top.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["标签", "频次"])
        w.writerows(c.most_common())

    print(f"\n输出目录: {args.out}")


if __name__ == "__main__":
    main()
