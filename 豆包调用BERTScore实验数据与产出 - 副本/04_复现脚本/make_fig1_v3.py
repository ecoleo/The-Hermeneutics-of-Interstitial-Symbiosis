# -*- coding: utf-8 -*-
"""图1（标注版v3）：双面板；每点标注模型名；同模型同色；
组内按值排序，偶数排名在左列、奇数排名在右列，两列各自纵向防重叠；
组均值文字置于柱底；人类基准文字置于轴左侧。"""
import json, os, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D

os.chdir(os.path.dirname(os.path.abspath(__file__)))
for fp in [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simsun.ttc']:
    fm.fontManager.addfont(fp)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

res = json.load(open('bertscore_result.json', encoding='utf-8'))
rows, summ = res['rows'], res['summary']
GROUPS = ['弱约束', '中约束', '强约束', '参照组']
MODELS = ["通义千问","文心一言","DeepSeek","Kimi","智谱清言","豆包","腾讯元宝","讯飞星火","MiniMax","阶跃星辰"]
SHORT = {"通义千问":"通义","文心一言":"文心","DeepSeek":"DeepSeek","Kimi":"Kimi","智谱清言":"智谱",
         "豆包":"豆包","腾讯元宝":"元宝","讯飞星火":"讯飞","MiniMax":"MiniMax","阶跃星辰":"阶跃"}
PAL = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
MCOL = dict(zip(MODELS, PAL))
human_f1 = res['human_vs_stories']['铸剑'][2]
YMIN, YMAX = 0.668, 0.818

def side_offsets(n, span=0.34):
    """偶数排名（0,2,4..）在左侧、奇数排名在右侧，各自均匀展开。"""
    off = np.zeros(n)
    left = [k for k in range(n) if k % 2 == 0]
    right = [k for k in range(n) if k % 2 == 1]
    for ids, sgn in ((left, -1), (right, 1)):
        m = len(ids)
        vals = np.linspace(0.05, span, m)
        for rank, xv in zip(ids, vals):
            off[rank] = sgn * xv
    return off

def draw_panel(ax, key, title, baseline=False):
    means = [summ[g][key] for g in GROUPS]
    sds = [summ[g][key+'_SD'] for g in GROUPS]
    xg = np.arange(4)
    ax.bar(xg, means, width=0.58, color='#EDEDED', zorder=1)
    for i,(m,s) in enumerate(zip(means,sds)):
        ax.errorbar(i, m, yerr=s, fmt='D', ms=7, color='#333', capsize=4, lw=1.3, zorder=4)
        ax.text(i, YMIN+0.004, '均值%.3f' % m, ha='center', va='bottom', fontsize=8.4, color='#555')
    if baseline:
        ax.axhline(human_f1, ls='--', lw=1.2, color='#555', zorder=2)
        ax.text(-0.55, 0.806, '虚线：人类样章对原作 F1=%.3f' % human_f1,
                ha='left', va='top', fontsize=8.4, color='#555',
                bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='none', alpha=0.85))
    for gi, g in enumerate(GROUPS):
        sub = sorted([r for r in rows if r['组']==g], key=lambda r: r[key])
        n = len(sub)
        xoffs = side_offsets(n)
        prev = {-1: -9, 1: -9}
        for k, r in enumerate(sub):
            yv = r[key]; xp = gi + xoffs[k]
            side = 1 if k % 2 else -1
            ax.scatter(xp, yv, s=34, color=MCOL[r['模型']], edgecolor='white', lw=.5, zorder=5)
            ly = yv
            if ly - prev[side] < 0.005:
                ly = prev[side] + 0.005
            if abs(ly-yv) > 0.0008:
                ax.plot([xp, xp + side*0.012], [yv, ly], lw=.5, color='#AAA', zorder=3)
            ax.text(xp + side*0.014, ly, SHORT[r['模型']], fontsize=7.8, va='center',
                    ha='left' if side > 0 else 'right', color='#222', zorder=6)
            prev[side] = ly
    ax.set_xticks(xg)
    ax.set_xticklabels(['%s\n(n=%d)' % (g, summ[g]['n']) for g in GROUPS], fontsize=10.5)
    ax.set_xlim(-0.6, 3.6); ax.set_ylim(YMIN, YMAX)
    ax.set_title(title, fontsize=11.5, pad=8)
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y', ls=':', alpha=.45, zorder=0)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(14, 8.6), dpi=300, sharey=True)
draw_panel(axL, 'F1_原作', '（甲）对鲁迅原作 F1（《故事新编》八篇多参照取最优）', baseline=True)
draw_panel(axR, 'F1_样章', '（乙）对人类《造字》样章 F1')
axL.set_ylabel('BERTScore F1（未缩放原始值）', fontsize=10.5)
fig.suptitle('图1  四组约束条件下各模型 BERTScore 语义相似度（灰柱为组均值、菱形±标准差、彩色点为各模型并标注名称）',
             fontsize=12.5, y=0.975)
handles = [Line2D([0],[0], marker='o', ls='', mfc=MCOL[m], mec='white', ms=8, label=SHORT[m]) for m in MODELS]
fig.legend(handles=handles, loc='lower center', ncol=10, frameon=False, fontsize=9,
           bbox_to_anchor=(0.5, -0.002), handletextpad=0.25, columnspacing=1.0)
axL.annotate('注：纵轴区间已截断（0.668–0.818）；为避免重叠，同组点按分值分列于中线左右，标签避让处以细灰线连接其真实数据点。',
             (0,0),(0,-0.115), xycoords='axes fraction', textcoords='axes fraction', fontsize=8.4, color='#777')
plt.tight_layout(rect=[0,0.03,1,0.955])
plt.savefig('fig1_group.png', bbox_inches='tight')
plt.close()
print('fig1 v3 saved')
