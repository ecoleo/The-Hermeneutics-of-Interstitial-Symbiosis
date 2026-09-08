# -*- coding: utf-8 -*-
"""BERTScore 三张分析图：分组层级、模型×组热力图、双参照散点。"""
import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch

for fp in [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simsun.ttc']:
    fm.fontManager.addfont(fp)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11

res = json.load(open('bertscore_result.json', encoding='utf-8'))
rows = res['rows']; summ = res['summary']
GROUPS = ['弱约束','中约束','强约束','参照组']
MODELS = ["通义千问","文心一言","DeepSeek","Kimi","智谱清言","豆包","腾讯元宝","讯飞星火","MiniMax","阶跃星辰"]
GC = {'弱约束':'#4E79A7','中约束':'#E1812C','强约束':'#59A14F','参照组':'#B07AA1'}
human_f1 = res['human_vs_stories']['铸剑'][2]  # 0.7448 人类样章 vs 原作最佳

# ---------- 图1：分组均值双系列 + 误差棒 + 人类基准 ----------
fig, ax = plt.subplots(figsize=(9.2, 5.4), dpi=300)
x = np.arange(4); w = 0.36
f1o = [summ[g]['F1_原作'] for g in GROUPS]
f1s = [summ[g]['F1_样章'] for g in GROUPS]
sdo = [summ[g]['F1_原作_SD'] for g in GROUPS]
sds = [summ[g]['F1_样章_SD'] for g in GROUPS]
b1 = ax.bar(x-w/2, f1o, w, yerr=sdo, capsize=4, color='#6B8FB5', label='对鲁迅原作 F1（八篇多参照取最优）',
            error_kw=dict(ecolor='#33495E', lw=1.1), zorder=2)
b2 = ax.bar(x+w/2, f1s, w, yerr=sds, capsize=4, color='#D08C60', label='对人类《造字》样章 F1',
            error_kw=dict(ecolor='#7A4B2E', lw=1.1), zorder=2)
for xi, v in zip(x-w/2, f1o): ax.text(xi, v+0.0015, f'{v:.3f}', ha='center', va='bottom', fontsize=9.5, color='#274259')
for xi, v in zip(x+w/2, f1s): ax.text(xi, v+0.0015, f'{v:.3f}', ha='center', va='bottom', fontsize=9.5, color='#7A4B2E')
ax.axhline(human_f1, ls='--', lw=1.3, color='#444', zorder=1)
ax.text(3.46, human_f1+0.0006, f'人类样章对鲁迅原作 F1={human_f1:.3f}', ha='right', va='bottom', fontsize=9.3, color='#444')
# 个体点
for gi, g in enumerate(GROUPS):
    grp = [r for r in rows if r['组']==g]
    ax.scatter([gi-w/2]*len(grp), [r['F1_原作'] for r in grp], s=16, color='#274259', alpha=.55, zorder=3)
    ax.scatter([gi+w/2]*len(grp), [r['F1_样章'] for r in grp], s=16, color='#7A4B2E', alpha=.55, zorder=3)
ax.set_xticks(x); ax.set_xticklabels([f'{g}\n(n={summ[g]["n"]})' for g in GROUPS])
ax.set_ylabel('BERTScore F1（未缩放原始值）')
ax.set_ylim(0.69, 0.812)
ax.set_title('图1  四组约束条件下 AI 生成文本的 BERTScore 语义相似度（组均值±标准差，点为各模型）', fontsize=12.5, pad=10)
ax.legend(loc='upper left', frameon=False, fontsize=9.6)
ax.spines[['top','right']].set_visible(False)
ax.grid(axis='y', ls=':', alpha=.45, zorder=0)
ax.annotate('纵轴区间已截断（0.69–0.81）', (0,0), (0.0,-0.13), xycoords='axes fraction', textcoords='axes fraction', fontsize=8.8, color='#777')
plt.tight_layout()
plt.savefig('fig1_group.png', bbox_inches='tight')
plt.close()

# ---------- 图2：模型×组 热力图（F1 样章） ----------
fig, ax = plt.subplots(figsize=(8.6, 6.6), dpi=300)
mat = np.full((10,4), np.nan)
for r in rows:
    i = MODELS.index(r['模型']); j = GROUPS.index(r['组'])
    mat[i,j] = r['F1_样章']
vmin, vmax = 0.68, 0.81
cmap = plt.cm.YlGnBu.copy(); cmap.set_bad('#E9E9E9')
im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')
for i in range(10):
    for j in range(4):
        v = mat[i,j]
        if np.isnan(v):
            ax.text(j,i,'未生成',ha='center',va='center',fontsize=9,color='#999')
        else:
            ax.text(j,i,f'{v:.3f}',ha='center',va='center',fontsize=9.3,
                    color='white' if v>0.775 else '#222')
xlabels = [f'{g}\n组均值 {summ[g]["F1_样章"]:.3f}' for g in GROUPS]
ax.set_xticks(range(4)); ax.set_xticklabels(xlabels, fontsize=10.5)
ax.set_yticks(range(10)); ax.set_yticklabels(MODELS, fontsize=10.5)
ax.set_title('图2  十模型×四约束组 BERTScore F1 矩阵（对人类《造字》样章）', fontsize=12.5, pad=10)
cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03); cb.set_label('F1', fontsize=10)
ax.set_ylim(9.5,-0.5)
plt.tight_layout()
plt.savefig('fig2_heatmap.png', bbox_inches='tight')
plt.close()

# ---------- 图3：双参照散点 ----------
fig, ax = plt.subplots(figsize=(9.2, 6.0), dpi=300)
for g in GROUPS:
    grp = [r for r in rows if r['组']==g]
    ax.scatter([r['F1_原作'] for r in grp], [r['F1_样章'] for r in grp],
               s=52, color=GC[g], label=f'{g}（n={len(grp)}）', edgecolor='white', lw=.6, zorder=3)
ax.axvline(human_f1, ls='--', lw=1.1, color='#666', zorder=1)
ax.text(human_f1, 0.8085, f' 人类样章对原作 F1={human_f1:.3f}', rotation=90, va='top', fontsize=9, color='#555')
# 标注离群/极值点
for r in rows:
    if (r['组']=='中约束' and r['模型'] in ('Kimi','阶跃星辰')) or (r['组']=='参照组' and r['模型']=='DeepSeek') or (r['模型']=='豆包' and r['组']=='强约束'):
        ax.annotate(f"{r['模型']}·{r['组'][0]}", (r['F1_原作'], r['F1_样章']),
                    xytext=(5,4), textcoords='offset points', fontsize=8.8, color='#333')
ax.set_xlabel('对鲁迅原作 F1（八篇多参照取最优）')
ax.set_ylabel('对人类《造字》样章 F1')
ax.set_xlim(0.672, 0.778); ax.set_ylim(0.672, 0.812)
ax.set_title('图3  38 篇生成文本在两类参照下的 BERTScore F1 分布（每点为一个模型×约束组）', fontsize=12.5, pad=10)
ax.legend(loc='lower right', frameon=False, fontsize=9.6)
ax.spines[['top','right']].set_visible(False)
ax.grid(ls=':', alpha=.45, zorder=0)
plt.tight_layout()
plt.savefig('fig3_scatter.png', bbox_inches='tight')
plt.close()
print('figures saved')
