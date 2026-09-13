# -*- coding: utf-8 -*-
"""
论文第五节分析图表生成（5 张，真实数据，300dpi PNG）。
运行：python charts.py
依赖：matplotlib（本机 3.11.1），数据文件位于 ../data。
输出：../交付_2026-09-12/02_图表/fig1..fig5.png
"""
import csv, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FIG = os.path.join(ROOT, "交付_2026-09-12", "02_图表")
os.makedirs(FIG, exist_ok=True)

C_COMP = "#3B7DDD"; C_PUB = "#E8A33D"; C_S1 = "#3B7DDD"; C_S3 = "#E8A33D"
GRID = dict(axis="y", alpha=0.3, linestyle="--")


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ---------------- 图1 B站 关键词×排序 类别构成 ----------------
rows = read_csv(os.path.join(DATA, "bili", "bili_category_stats.csv"))
kws = ["故事新编 鲁迅", "故事新编", "鲁迅"]
cats = ["幽默解构类", "文学品质类", "知识教育类", "有声说书类"]
cat_colors = {"幽默解构类": "#C0504D", "文学品质类": "#3B7DDD",
              "知识教育类": "#6AA84F", "有声说书类": "#999999"}
fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharey=True)
x = np.arange(len(cats)); wdt = 0.36
for ax, kw in zip(axes, kws):
    for i, (order, label, color_edge) in enumerate(
            [("totalrank", "综合排序", C_COMP), ("pubdate", "最新排序", C_PUB)]):
        vals, los, his = [], [], []
        for c in cats:
            r = next(r for r in rows if r["关键词"] == kw and r["排序"] == order and r["类别"] == c)
            vals.append(float(r["占比%"]))
            los.append(float(r["占比%"]) - float(r["CI下限%"]))
            his.append(float(r["CI上限%"]) - float(r["占比%"]))
        ax.bar(x + (i - 0.5) * wdt, vals, wdt * 0.92,
               yerr=[los, his], capsize=3,
               color=[cat_colors[c] for c in cats], alpha=0.55 + 0.45 * i,
               edgecolor="black", linewidth=0.4, label=label)
    ax.set_xticks(x); ax.set_xticklabels([c.replace("类", "") for c in cats], fontsize=9)
    ax.set_title(f"关键词「{kw}」", fontsize=11)
    ax.grid(**GRID); ax.set_axisbelow(True)
from matplotlib.patches import Patch
axes[0].legend(handles=[Patch(facecolor="#888888", alpha=0.55, label="综合排序"),
                        Patch(facecolor="#888888", alpha=1.0, label="最新排序")],
               fontsize=8, frameon=False, loc="upper right")
fig.legend(handles=[Patch(facecolor=cat_colors[c], label=c) for c in cats],
           fontsize=9, frameon=False, loc="lower center", ncol=4)
axes[0].set_ylabel("类别标签命中占比（%，含95%置信区间）")
fig.suptitle("图5-1  B站《故事新编》相关视频标签类别构成：关键词×排序（N=797，2026-09-11）",
             fontsize=12, y=1.00)
fig.tight_layout(rect=[0, 0.07, 1, 1])
fig.savefig(os.path.join(FIG, "fig1_bili_composition.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------- 图2 B站 综合vs最新 构成差异（哑铃图） ----------------
tests = read_csv(os.path.join(DATA, "bili", "bili_order_tests.csv"))
fig, ax = plt.subplots(figsize=(8.6, 5.2))
ylabels, ypos = [], []
y = 0
for kw in kws:
    for c in cats:
        r1 = next(r for r in rows if r["关键词"] == kw and r["排序"] == "totalrank" and r["类别"] == c)
        r2 = next(r for r in rows if r["关键词"] == kw and r["排序"] == "pubdate" and r["类别"] == c)
        t = next(t for t in tests if t["关键词"] == kw and t["类别"] == c)
        v1, v2 = float(r1["占比%"]), float(r2["占比%"])
        sig = t["判读"] == "显著"
        ax.plot([v1, v2], [y, y], color="#BBBBBB", lw=1.6, zorder=1)
        ax.scatter([v1], [y], s=52, color=C_COMP, zorder=2)
        ax.scatter([v2], [y], s=52, color=C_PUB, zorder=2)
        mark = f"  z={t['z']}, p={float(t['p']):.4f}{' *' if sig else ' ns'}"
        ax.text(max(v1, v2) + 1.5, y, mark, va="center", fontsize=8,
                color="#C00000" if sig else "#888888")
        ylabels.append(f"{kw}｜{c.replace('类', '')}")
        ypos.append(y); y += 1
ax.set_yticks(ypos); ax.set_yticklabels(ylabels, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("类别标签命中占比（%）　蓝=综合排序　橙=最新排序　（* p<.05）")
ax.set_title("图5-2  B站排序逻辑对可见性的再分配：综合排序 vs 最新排序构成差异（两比例z检验）",
             fontsize=11)
ax.grid(axis="x", alpha=0.3, linestyle="--"); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_bili_order_effect.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------- 图3 豆瓣 星级分布+高频词 ----------------
dstat = json.load(open(os.path.join(DATA, "douban_2046909_merged_stats", "stats.json"),
                       encoding="utf-8"))
merged = [json.loads(l) for l in open(
    os.path.join(DATA, "douban_2046909_merged.jsonl"), encoding="utf-8")]
from collections import Counter
rc = Counter(r.get("rating") for r in merged if r.get("rating"))
kw_all = read_csv(os.path.join(DATA, "douban_2046909_merged_stats", "keywords_top.csv"))
# 图示用词过滤：剔除无语义区分度的功能词（过滤词表同步记录于复现说明）
STOP = {"最", "写", "但", "得", "太", "多", "来", "大", "却", "有些", "这种",
        "一篇", "现在", "时候", "懂", "爱", "作品", "小时侯", "小时候"}
kw_rows = [r for r in kw_all if r["关键词"] not in STOP][:12]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.2))
stars = [5, 4, 3, 2, 1]
cnt = [rc.get(s, 0) for s in stars]
bars = a1.bar([str(s) + "星" for s in stars], cnt, color="#3B7DDD", alpha=0.85)
for b, c in zip(bars, cnt):
    a1.text(b.get_x() + b.get_width() / 2, c + 4, str(c), ha="center", fontsize=10)
a1.set_title("（a）「读过」短评星级分布（有效评分n=455）", fontsize=10.5)
a1.set_ylabel("短评数"); a1.grid(**GRID); a1.set_axisbelow(True)
words = [r["关键词"] for r in kw_rows][::-1]
freqs = [int(r["词频"]) for r in kw_rows][::-1]
a2.barh(words, freqs, color="#6AA84F", alpha=0.85)
a2.set_title("（b）短评高频词TOP12（jieba+TF-IDF，N=497）", fontsize=10.5)
a2.set_xlabel("词频"); a2.grid(axis="x", alpha=0.3, linestyle="--"); a2.set_axisbelow(True)
fig.suptitle("图5-3  豆瓣《故事新编》(#2046909)「读过」短评：评价高度正面且文学化（2026-09-11/12采样）",
             fontsize=12, y=1.00)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_douban.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------- 图4 微信读书 S1点评 vs S3想法 ----------------
coding = read_csv(os.path.join(DATA, "weread_coding_by_stratum.csv"))
cats4 = ["讽刺批判/当代迁移", "情感共鸣/个人经验", "文学专业维度", "篇目/人物指涉"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(len(cats4)); wdt = 0.34
for i, (src, label, color) in enumerate([("S1", "书级点评（n=209）", C_S1),
                                         ("S3", "划线下想法（n=827）", C_S3)]):
    vals, los, his = [], [], []
    for c in cats4:
        r = next(r for r in coding if r["stratum"] == src and r["category"] == c)
        p, lo, hi = float(r["proportion"]) * 100, float(r["ci95_low"]) * 100, float(r["ci95_high"]) * 100
        vals.append(p); los.append(p - lo); his.append(hi - p)
    b = ax.bar(x + (i - 0.5) * wdt, vals, wdt * 0.9, yerr=[los, his],
               capsize=4, color=color, alpha=0.88, label=label)
    for rect, v in zip(b, vals):
        ax.text(rect.get_x() + rect.get_width() / 2, v + 2.2, f"{v:.1f}",
                ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(cats4, fontsize=10)
ax.set_ylabel("预登记词典命中比例（%，含95%置信区间）")
ax.set_title("图5-4  微信读书「读者说」主题结构：书级点评与划线下想法的分层对比（N=1036，2026-09-12）",
             fontsize=11)
ax.legend(frameon=False); ax.grid(**GRID); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_weread_strata.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------------- 图5 微信读书 热门划线 ----------------
pm_rows = read_csv(os.path.join(DATA, "weread_bookmarks_pianmu.csv"))
top_rows = read_csv(os.path.join(DATA, "weread_bookmarks_top.csv"))[:10]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1, 1.5]})
pm = [r["pianmu"] for r in pm_rows]
nb = [int(r["n_bookmarks"]) for r in pm_rows]
persons = [int(r["total_mark_persons"]) for r in pm_rows]
x = np.arange(len(pm))
bars = a1.bar(x, nb, 0.62, color=C_S1, alpha=0.88)
for xi, n_, p_ in zip(x, nb, persons):
    a1.text(xi, n_ + 1.5, f"{n_}条\n{p_}人次", ha="center", fontsize=7.5)
a1.set_xticks(x); a1.set_xticklabels(pm, fontsize=9, rotation=30)
a1.set_ylim(0, max(nb) * 1.32)
a1.set_ylabel("热门划线条数")
a1.set_title("（a）热门划线的篇目分布（N=400；柱上同时标注划线人次）", fontsize=10)
a1.grid(**GRID); a1.set_axisbelow(True)
labels = [f"{r['pianmu']}｜{r['markText'][:18]}…" for r in top_rows][::-1]
vals = [int(r["mark_persons"]) for r in top_rows][::-1]
a2.barh(labels, vals, color="#3B7DDD", alpha=0.85)
for i, v in enumerate(vals):
    a2.text(v + 12, i, str(v), va="center", fontsize=8.5)
a2.set_title("（b）热门划线TOP10（按划线人数）", fontsize=10)
a2.set_xlabel("划线人数"); a2.grid(axis="x", alpha=0.3, linestyle="--"); a2.set_axisbelow(True)
a2.tick_params(labelsize=8.5)
fig.suptitle("图5-5  微信读书《故事新编》章节热门划线：篇目分布与TOP10（2026-09-12）",
             fontsize=12, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig5_weread_bookmarks.png"), dpi=300, bbox_inches="tight")
plt.close(fig)

print("OK ->", os.listdir(FIG))
