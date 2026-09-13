# -*- coding: utf-8 -*-
"""汇总四平台论文引用所需的全部关键统计量（全部由原始数据现算，落盘 summary_stats.json）。"""
import csv
import json
import os
import statistics
from collections import Counter

BASE = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判'
ANA = os.path.join(BASE, 'data', 'analysis')
os.makedirs(ANA, exist_ok=True)
S = {}

# ---------- B站 ----------
cat = list(csv.DictReader(open(os.path.join(BASE, 'data/bili/bili_category_stats.csv'), encoding='utf-8')))
tests = list(csv.DictReader(open(os.path.join(BASE, 'data/bili/bili_order_tests.csv'), encoding='utf-8')))
tags = list(csv.reader(open(os.path.join(BASE, 'data/bili/bili_tags_top.csv'), encoding='utf-8')))[1:]
bili = {'total_n': 797, 'by_kw_order': {}, 'tests': tests, 'top_tags': [(t, int(n)) for t, n in tags[:12]]}
for r in cat:
    k = '%s|%s' % (r['关键词'], '综合' if r['排序'] == 'totalrank' else '最新')
    bili['by_kw_order'].setdefault(k, {})[r['类别']] = {
        'n': int(r['样本量']), 'x': int(r['命中数']), 'pct': float(r['占比%'])}
S['bili'] = bili

# ---------- 豆瓣 ----------
dst = json.load(open(os.path.join(BASE, 'data/douban_2046909_auth/stats.json'), encoding='utf-8'))
rate = list(csv.DictReader(open(os.path.join(BASE, 'data/douban_2046909_auth/rating_distribution.csv'), encoding='utf-8-sig')))
kw = list(csv.reader(open(os.path.join(BASE, 'data/douban_2046909_auth/keywords_top.csv'), encoding='utf-8')))[1:]
stop = {'最', '太', '但', '却', '于', '地', '得', '为', '新', '写', '起来', '时候', '有些', '作品'}
kw_content = [(w, int(n)) for w, n, _ in kw if w not in stop][:15]
# 检查网络流行词：以原始短评全文做精确子串计数（不依赖jieba是否切词、不依赖是否进Top表）
_db_lines = [json.loads(_l)['text'] for _l in open(
    os.path.join(BASE, 'data/douban_2046909_auth/comments_2046909_P.jsonl'), encoding='utf-8')]
_db_alltext = ''.join(_db_lines)
buzzwords = ['毒舌', '吐槽', '爽文', '嘴替', '互联网嘴替', '魔改', '整活', '玩梗']
crit_words = ['解构', '戏谑', '荒诞', '讽刺', '反讽', '幽默']
douban = {
    'n': dst['n_comments'], 'declared_total': dst['declared_total'],
    'coverage_pct': round(dst['coverage'] * 100, 2),
    'mean': dst['rating_mean'], 'rating_dist': {r['星级']: {'n': int(r['条数']), 'pct': float(r['占比%'])} for r in rate},
    'top_content_words': kw_content,
    'buzzword_substr_count': {b: _db_alltext.count(b) for b in buzzwords},
    'critique_substr_count': {b: _db_alltext.count(b) for b in crit_words},
}
S['douban'] = douban

# ---------- 微信读书 ----------
wr = json.load(open(os.path.join(BASE, 'data', 'weread_故事新编_采集_2026-09-12.json'), encoding='utf-8'))
b = wr['40509933']
PIAN = {4: '序言', 5: '补天', 6: '补天', 7: '补天', 8: '奔月', 10: '奔月', 12: '理水', 13: '理水',
        18: '采薇', 20: '铸剑', 22: '铸剑', 30: '非攻', 31: '非攻'}
pian_count = Counter(PIAN.get(it['chapterUid'], '其他') for it in b['bestbookmarks']['items'])
star_count = Counter()
for it in b['reviews']['items']:
    inner = it['review'].get('review', {})
    star_count[inner.get('star')] += 1
weread = {
    'bookId': 40509933,
    'highlight_total': b['bestbookmarks']['totalCount'], 'highlight_returned': b['bestbookmarks']['n'],
    'review_total': b['reviews']['reviewsCnt'], 'review_returned': b['reviews']['n'],
    'top5_highlights': [(it['totalCount'], (it['markText'] or '')[:30]) for it in b['bestbookmarks']['items'][:5]],
    'pian_distribution_top20': dict(pian_count),
    'review_star_dist': dict(star_count),
}
S['weread'] = weread

# ---------- 抖音 ----------
rows = list(csv.DictReader(open(os.path.join(BASE, 'data/douyin/douyin_parsed.csv'), encoding='utf-8-sig')))
cats = ['名句呈现类', '仿写玩梗类', '共鸣纪念类', '知识讲解类', '剧情演绎类', '无关混入', '其他']
dy = {}
for q in ['鲁迅说', '故事新编 鲁迅']:
    sub = [r for r in rows if r['query'] == q]
    n = len(sub)
    dist = {c: sum(1 for r in sub if r['内容形式主类'] == c) for c in cats}
    rel = [r for r in sub if r['内容形式主类'] != '无关混入']
    nr = len(rel)
    rel_dist = {c: sum(1 for r in rel if r['内容形式主类'] == c) for c in cats}
    likes = [int(r['点赞数']) for r in sub if r['点赞数'] not in ('', 'None') and r['点赞数'] is not None]
    likes = [x for x in likes if x >= 0]
    img = sum(1 for r in sub if r['载体形式'] == '图文')
    tagc = Counter(t for r in sub for t in r['话题标签'].split(';') if t)
    frag = sum(dist[c] for c in ['名句呈现类', '仿写玩梗类', '共鸣纪念类'])
    deep = sum(dist[c] for c in ['知识讲解类', '剧情演绎类'])
    dy[q] = {
        'n': n, 'dist': dist,
        'pct_all': {c: round(dist[c] / n * 100, 1) for c in cats},
        'relevant_n': nr,
        'pct_relevant': {c: round(rel_dist[c] / nr * 100, 1) for c in cats},
        'frag_pct_all': round(frag / n * 100, 1), 'deep_pct_all': round(deep / n * 100, 1),
        'frag_pct_relevant': round(frag / nr * 100, 1), 'deep_pct_relevant': round(deep / nr * 100, 1),
        'image_n': img, 'video_n': n - img,
        'likes_median': statistics.median(likes) if likes else None,
        'likes_mean': round(statistics.mean(likes), 0) if likes else None,
        'likes_ge_1w': sum(1 for x in likes if x >= 10000),
        'likes_max': max(likes) if likes else None,
        'top_tags': tagc.most_common(12),
    }
S['douyin'] = dy

with open(os.path.join(ANA, 'summary_stats.json'), 'w', encoding='utf-8') as f:
    json.dump(S, f, ensure_ascii=False, indent=2)

# 打印关键结果
print('========== 论文引用关键数字汇总 ==========')
print('\n【B站】总797')
for k in ['故事新编 鲁迅|综合', '故事新编 鲁迅|最新']:
    print(' ', k, {c: round(v['pct'], 1) for c, v in bili['by_kw_order'][k].items()})
print('  故事新编鲁迅 显著检验:', [(t['类别'], t['z'], t['p'], t['判读']) for t in tests if t['关键词'] == '故事新编 鲁迅'])
print('  Top标签:', bili['top_tags'][:8])
print('\n【豆瓣】', douban['n'], '覆盖率', douban['coverage_pct'], '均分', douban['mean'])
print('  星级:', {k: v['n'] for k, v in douban['rating_dist'].items()})
print('  实词Top12:', kw_content[:12])
print('  消遣词子串计数:', douban['buzzword_substr_count'])
print('  批评词子串计数:', douban['critique_substr_count'])
print('\n【微信读书】划线总', weread['highlight_total'], '返回', weread['highlight_returned'],
      '点评总', weread['review_total'], '返回', weread['review_returned'])
print('  TOP5:', weread['top5_highlights'])
print('  Top20篇目分布:', weread['pian_distribution_top20'])
print('  点评星级:', weread['review_star_dist'])
print('\n【抖音】')
for q, v in dy.items():
    print(' ', q, 'n=%d 图文%d/视频%d' % (v['n'], v['image_n'], v['video_n']))
    print('   全样本占比:', v['pct_all'])
    print('   相关样本n=%d 占比:' % v['relevant_n'], v['pct_relevant'])
    print('   碎片%.1f%% 深度%.1f%%（相关样本 碎片%.1f%% 深度%.1f%%）' % (
        v['frag_pct_all'], v['deep_pct_all'], v['frag_pct_relevant'], v['deep_pct_relevant']))
    print('   点赞中位%s 均值%s ≥1万:%d 最大%s' % (v['likes_median'], v['likes_mean'], v['likes_ge_1w'], v['likes_max']))
    print('   高频标签:', v['top_tags'][:8])
print('\n已落盘 data/analysis/summary_stats.json')
