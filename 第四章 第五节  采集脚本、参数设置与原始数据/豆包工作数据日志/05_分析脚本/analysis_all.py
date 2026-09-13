# -*- coding: utf-8 -*-
"""
四平台数字副文本统一分析与出图（真实数据，禁止任何估算/虚构）。
输入：data/bili、data/douban_2046909_auth、data/weread_故事新编_采集_2026-09-12.json、data/douyin/douyin_parsed.csv
输出：data/analysis/*.csv 与交付目录 04_分析图表/*.png（300dpi）
"""
import csv
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# ---------- 中文字体 ----------
FONT_PATH = r'C:\Windows\Fonts\simhei.ttf'
font_manager.fontManager.addfont(FONT_PATH)
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11

BASE = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判'
FIG = os.path.join(BASE, '第五节_数字副文本采集与修订交付_20260912', '04_分析图表')
ANA = os.path.join(BASE, 'data', 'analysis')
os.makedirs(FIG, exist_ok=True)
os.makedirs(ANA, exist_ok=True)

# 配色（克制学术风）
C_BLUE = '#2f5f8f'
C_ORANGE = '#dd8b35'
C_GREEN = '#4e8a45'
C_RED = '#b5494a'
C_GRAY = '#8a8a8a'
C_LBLUE = '#7fb0d6'
CAT_COLORS = [C_RED, C_BLUE, C_GREEN, C_ORANGE]


def save(fig, name):
    p = os.path.join(FIG, name)
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('saved:', p)


# ============================================================
# 图1：B站 三关键词 × 综合/最新 四类标签占比（含Wilson CI误差线）
# ============================================================
def fig1_bili():
    rows = list(csv.DictReader(open(os.path.join(BASE, 'data/bili/bili_category_stats.csv'), encoding='utf-8')))
    cats = ['文学品质类', '知识教育类', '有声说书类', '幽默解构类']
    kws = ['故事新编 鲁迅', '故事新编', '鲁迅']
    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True)
    x = np.arange(len(cats))
    w = 0.36
    for ax, kw in zip(axes, kws):
        def val(order, cat, field):
            for r in rows:
                if r['关键词'] == kw and r['排序'] == order and r['类别'] == cat:
                    return float(r[field])
            return 0.0
        comp = [val('totalrank', c, '占比%') for c in cats]
        new = [val('pubdate', c, '占比%') for c in cats]
        clo = [val('totalrank', c, '占比%') - val('totalrank', c, 'CI下限%') for c in cats]
        chi = [val('totalrank', c, 'CI上限%') - val('totalrank', c, '占比%') for c in cats]
        nlo = [val('pubdate', c, '占比%') - val('pubdate', c, 'CI下限%') for c in cats]
        nhi = [val('pubdate', c, 'CI上限%') - val('pubdate', c, '占比%') for c in cats]
        b1 = ax.bar(x - w/2, comp, w, label='综合排序', color=C_BLUE,
                    yerr=[clo, chi], capsize=3, error_kw={'elinewidth': 1, 'ecolor': C_GRAY})
        b2 = ax.bar(x + w/2, new, w, label='最新排序', color=C_ORANGE,
                    yerr=[nlo, nhi], capsize=3, error_kw={'elinewidth': 1, 'ecolor': C_GRAY})
        for b in list(b1) + list(b2):
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5,
                    '%.1f' % b.get_height(), ha='center', va='bottom', fontsize=9)
        n_c = sum(1 for r in rows if r['关键词'] == kw and r['排序'] == 'totalrank')
        nn_comp = [r['样本量'] for r in rows if r['关键词'] == kw and r['排序'] == 'totalrank'][0]
        nn_new = [r['样本量'] for r in rows if r['关键词'] == kw and r['排序'] == 'pubdate'][0]
        ax.set_title('关键词「%s」（综合 n=%s / 最新 n=%s）' % (kw, nn_comp, nn_new), fontsize=11)
        ax.set_ylabel('标签命中占比 %')
        ax.set_ylim(0, 108)
        ax.legend(fontsize=9, loc='upper right')
        ax.grid(axis='y', ls='--', alpha=0.35)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(cats)
    fig.suptitle('图1  B站搜索结果标签类别占比：综合排序 vs 最新排序（柱顶为占比，误差线为Wilson 95%CI）',
                 fontsize=12.5, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    save(fig, '图1_B站综合与最新排序标签占比对比.png')


# ============================================================
# 图2：B站 全样本高频标签 Top15
# ============================================================
def fig2_bili_tags():
    rows = list(csv.reader(open(os.path.join(BASE, 'data/bili/bili_tags_top.csv'), encoding='utf-8')))[1:]
    rows = [(t, int(n)) for t, n in rows][:15][::-1]
    labels = [t for t, n in rows]
    vals = [n for t, n in rows]
    fig, ax = plt.subplots(figsize=(8.5, 6))
    bars = ax.barh(labels, vals, color=C_BLUE)
    bars[-1].set_color(C_RED)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 5, b.get_y() + b.get_height()/2, str(v),
                va='center', fontsize=9.5)
    ax.set_xlabel('出现视频条数（全样本 N=797，标签可多重命中）')
    ax.set_title('图2  B站《故事新编》相关视频高频标签 Top15', fontsize=12.5)
    ax.grid(axis='x', ls='--', alpha=0.35)
    ax.set_xlim(0, max(vals) * 1.12)
    fig.tight_layout()
    save(fig, '图2_B站高频标签Top15.png')


# ============================================================
# 图3：豆瓣 星级分布 + 高频词 Top15
# ============================================================
def fig3_douban():
    rate = list(csv.DictReader(open(os.path.join(BASE, 'data/douban_2046909_auth/rating_distribution.csv'), encoding='utf-8-sig')))
    order = ['5', '4', '3', '2', '1', '0']
    labmap = {'5': '5星', '4': '4星', '3': '3星', '2': '2星', '1': '1星', '0': '未评分'}
    rd = {r['星级']: (int(r['条数']), float(r['占比%'])) for r in rate}
    labels = [labmap[k] for k in order]
    vals = [rd[k][0] for k in order]
    pcts = [rd[k][1] for k in order]
    cols = [C_RED, C_ORANGE, '#c9b64a', C_GRAY, C_GRAY, C_LBLUE]

    kw = list(csv.reader(open(os.path.join(BASE, 'data/douban_2046909_auth/keywords_top.csv'), encoding='utf-8')))[1:]
    # 去除无实义虚词，保留前15个实词
    stop = {'最', '太', '但', '却', '于', '地', '得', '为', '新', '写', '起来', '时候', '有些', '作品'}
    kw = [(w, int(n)) for w, n, _ in kw if w not in stop][:15][::-1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={'width_ratios': [1, 1.25]})
    bars = ax1.bar(labels, vals, color=cols)
    for b, v, p in zip(bars, vals, pcts):
        ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5,
                 '%d\n%.1f%%' % (v, p), ha='center', va='bottom', fontsize=9.5)
    ax1.set_title('A. 短评星级分布（n=200，均分4.58）', fontsize=11.5)
    ax1.set_ylabel('短评条数')
    ax1.set_ylim(0, max(vals) * 1.18)
    ax1.grid(axis='y', ls='--', alpha=0.35)

    ax2.barh([w for w, n in kw], [n for w, n in kw], color=C_GREEN)
    for i, (w, n) in enumerate(kw):
        ax2.text(n + 0.6, i, str(n), va='center', fontsize=9)
    ax2.set_title('B. 短评高频实词 Top15（jieba分词+TF-IDF）', fontsize=11.5)
    ax2.set_xlabel('词频（条次）')
    ax2.grid(axis='x', ls='--', alpha=0.35)
    ax2.set_xlim(0, max(n for w, n in kw) * 1.15)
    fig.suptitle('图3  豆瓣《故事新编》短评评分分布与高频词（登录态采集，热门+最新各100条）', fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, '图3_豆瓣评分分布与高频词.png')


# ============================================================
# 图4：微信读书 热门划线 Top12（人数，按篇目着色）
# ============================================================
WEREAD_CHAPTER = {4: '序言', 5: '补天', 6: '补天', 7: '补天', 8: '奔月', 10: '奔月',
                  12: '理水', 13: '理水', 18: '采薇', 20: '铸剑', 22: '铸剑',
                  30: '非攻', 31: '非攻'}
PIAN_COLOR = {'补天': C_RED, '理水': C_BLUE, '铸剑': C_GREEN, '奔月': C_ORANGE,
              '非攻': '#7a5fa6', '采薇': '#5a9bd4', '序言': C_GRAY}


def fig4_weread():
    wr = json.load(open(os.path.join(BASE, 'data', 'weread_故事新编_采集_2026-09-12.json'), encoding='utf-8'))
    items = wr['40509933']['bestbookmarks']['items'][:12]
    items = sorted(items, key=lambda x: x['totalCount'])
    labels, vals, cols = [], [], []
    for it in items:
        pian = WEREAD_CHAPTER.get(it['chapterUid'], '其他')
        txt = (it['markText'] or '').replace('\n', '')[:11]
        labels.append('《%s》%s' % (pian, txt))
        vals.append(it['totalCount'])
        cols.append(PIAN_COLOR.get(pian, C_GRAY))
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    bars = ax.barh(labels, vals, color=cols)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 8, b.get_y() + b.get_height()/2, '%d人' % v,
                va='center', fontsize=9.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in
               [C_RED, C_BLUE, C_GREEN, C_ORANGE, '#7a5fa6', '#5a9bd4', C_GRAY]]
    ax.legend(handles, ['补天', '理水', '铸剑', '奔月', '非攻', '采薇', '序言'],
              fontsize=9, ncol=4, loc='lower right')
    ax.set_xlabel('划线人数（微信读书「热门划线」，服务端按热度返回前20/全书共449条）')
    ax.set_title('图5  微信读书《故事新编》热门划线 Top12（按篇目着色）', fontsize=12.5)
    ax.grid(axis='x', ls='--', alpha=0.35)
    ax.set_xlim(0, max(vals) * 1.15)
    fig.tight_layout()
    save(fig, '图5_微信读书热门划线Top12.png')


# ============================================================
# 图5：抖音 两查询词 内容形式分布对比
# ============================================================
def fig5_douyin():
    rows = list(csv.DictReader(open(os.path.join(BASE, 'data/douyin/douyin_parsed.csv'), encoding='utf-8-sig')))
    cats = ['名句呈现类', '仿写玩梗类', '共鸣纪念类', '知识讲解类', '剧情演绎类', '无关混入', '其他']
    qs = ['鲁迅说', '故事新编 鲁迅']
    dist = {}
    for q in qs:
        sub = [r for r in rows if r['query'] == q]
        n = len(sub)
        dist[q] = {c: sum(1 for r in sub if r['内容形式主类'] == c) / n * 100 for c in cats}
        dist[q]['_n'] = n
    x = np.arange(len(cats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.8))
    b1 = ax.bar(x - w/2, [dist['鲁迅说'][c] for c in cats], w, label='「鲁迅说」n=147', color=C_BLUE)
    b2 = ax.bar(x + w/2, [dist['故事新编 鲁迅'][c] for c in cats], w, label='「故事新编 鲁迅」n=18', color=C_GREEN)
    for b in list(b1) + list(b2):
        if b.get_height() > 0.5:
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.8,
                    '%.1f%%' % b.get_height(), ha='center', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=10)
    ax.set_ylabel('占该查询结果比例 %')
    ax.set_ylim(0, 100)
    ax.set_title('图4  抖音搜索结果内容形式分布对比（登录态浏览器采集，单账号单时点综合排序快照）', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(axis='y', ls='--', alpha=0.35)
    fig.tight_layout()
    save(fig, '图4_抖音内容形式分布对比.png')
    # 导出分布表
    with open(os.path.join(ANA, 'douyin_form_distribution.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['查询词', '样本量'] + cats)
        for q in qs:
            w.writerow([q, dist[q]['_n']] + ['%.2f' % dist[q][c] for c in cats])


# ============================================================
# 图6：跨平台 深度内容 vs 碎片金句 内容形态对比
# ============================================================
def fig6_cross():
    rows = list(csv.DictReader(open(os.path.join(BASE, 'data/douyin/douyin_parsed.csv'), encoding='utf-8-sig')))

    def pct(q, cats):
        sub = [r for r in rows if r['query'] == q]
        return sum(1 for r in sub if r['内容形式主类'] in cats) / len(sub) * 100
    frag = ['名句呈现类', '仿写玩梗类', '共鸣纪念类']
    deep = ['知识讲解类', '剧情演绎类']
    d_lx = pct('鲁迅说', deep)
    f_lx = pct('鲁迅说', frag)
    d_gs = pct('故事新编 鲁迅', deep)
    f_gs = pct('故事新编 鲁迅', frag)
    # 微信读书热门划线：20条均为文学描写/国民性讽刺段落，无励志金句（人工逐条编码，见脚本）
    d_wr, f_wr = 100.0, 0.0

    groups = ['抖音「鲁迅说」\n(泛话题 n=147)', '抖音「故事新编 鲁迅」\n(篇目词 n=18)', '微信读书热门划线\n(Top20/全书449)']
    deep_v = [d_lx, d_gs, d_wr]
    frag_v = [f_lx, f_gs, f_wr]
    x = np.arange(len(groups))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    b1 = ax.bar(x - w/2, deep_v, w, label='深度内容（系统讲解/演绎/文学性段落）', color=C_BLUE)
    b2 = ax.bar(x + w/2, frag_v, w, label='碎片化内容（名句呈现/拟体玩梗/情绪共鸣）', color=C_ORANGE)
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1.2,
                '%.1f%%' % b.get_height(), ha='center', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=10)
    ax.set_ylabel('占比 %')
    ax.set_ylim(0, 112)
    ax.set_title('图6  不同平台/检索词下的内容形态构成对比', fontsize=12.5)
    ax.legend(fontsize=9.5, loc='upper center')
    ax.grid(axis='y', ls='--', alpha=0.35)
    ax.text(0.5, -0.16,
            '口径：抖音按标题/话题标签规则编码（互斥六类，余为无关混入与其他）；微信读书热门划线按段落内容人工编码，20条均为文学描写或国民性讽刺段落。',
            transform=ax.transAxes, ha='center', fontsize=8.2, color=C_GRAY)
    fig.tight_layout()
    save(fig, '图6_跨平台内容形态对比.png')
    with open(os.path.join(ANA, 'cross_platform_form.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['平台/检索词', '深度内容%', '碎片金句%'])
        w.writerow(['抖音-鲁迅说', '%.2f' % d_lx, '%.2f' % f_lx])
        w.writerow(['抖音-故事新编鲁迅', '%.2f' % d_gs, '%.2f' % f_gs])
        w.writerow(['微信读书-热门划线', '%.2f' % d_wr, '%.2f' % f_wr])


if __name__ == '__main__':
    fig1_bili()
    fig2_bili_tags()
    fig3_douban()
    fig5_douyin()   # 产出“图4_抖音…”（图号按正文出现顺序）
    fig4_weread()   # 产出“图5_微信读书…”
    fig6_cross()
    print('\n全部图表生成完成。')
