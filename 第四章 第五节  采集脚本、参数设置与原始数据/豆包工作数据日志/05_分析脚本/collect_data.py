# -*- coding: utf-8 -*-
"""归集四平台数据到交付目录02，并对自然人昵称/数字UID做稳定匿名化。"""
import os, json, re, csv, shutil

BASE = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判'
DEL = os.path.join(BASE, '第五节_数字副文本采集与修订交付_20260912', '02_平台采集数据')
for sub in ['B站', '豆瓣', '抖音', '微信读书', '汇总统计']:
    os.makedirs(os.path.join(DEL, sub), exist_ok=True)

def copy(src, dst):
    shutil.copy(os.path.join(BASE, src), os.path.join(DEL, dst))

# ---------- B站：匿名 author、移除 mid ----------
up_map = {}
def anon_up(name):
    if name not in up_map:
        up_map[name] = 'UP_%03d' % (len(up_map)+1)
    return up_map[name]
for kw in ['故事新编鲁迅', '故事新编', '鲁迅']:
    src = r'data\bili\bili_%s.jsonl' % kw
    out = os.path.join(DEL, 'B站', 'bili_%s_anon.jsonl' % kw)
    n = 0
    with open(os.path.join(BASE, src), encoding='utf-8') as f, open(out, 'w', encoding='utf-8') as g:
        for line in f:
            o = json.loads(line)
            o['author'] = anon_up(o.get('author', ''))
            o.pop('mid', None)
            g.write(json.dumps(o, ensure_ascii=False) + '\n'); n += 1
    copy(r'data\bili\bili_%s_meta.json' % kw, os.path.join('B站', 'bili_%s_meta.json' % kw))
    print('B站', kw, n)
for f in ['bili_category_stats.csv', 'bili_order_tests.csv', 'bili_tags_top.csv']:
    copy(os.path.join('data','bili',f), os.path.join('B站',f))

# ---------- 豆瓣：匿名 user ----------
rd_map = {}
def anon_rd(name):
    if name not in rd_map:
        rd_map[name] = '读者_%03d' % (len(rd_map)+1)
    return rd_map[name]
src = r'data\douban_2046909_auth\comments_2046909_P.jsonl'
out = os.path.join(DEL, '豆瓣', 'comments_2046909_anon.jsonl')
n = 0
with open(os.path.join(BASE, src), encoding='utf-8') as f, open(out, 'w', encoding='utf-8') as g:
    for line in f:
        o = json.loads(line)
        o['user'] = anon_rd(o.get('user', ''))
        g.write(json.dumps(o, ensure_ascii=False) + '\n'); n += 1
print('豆瓣', n)
for f in ['stats.json','meta_2046909_P.json','keywords_top.csv','rating_distribution.csv',
          'rating_title_distribution.csv','keywords_by_rating.csv','length_distribution.csv',
          'top_comments.csv','yearly_trend.csv','yearly_keywords.csv']:
    p = os.path.join('data','douban_2046909_auth',f)
    if os.path.exists(os.path.join(BASE,p)):
        copy(p, os.path.join('豆瓣',f))

# ---------- 抖音：raw 正则去 @昵称；parsed.csv 匿名作者列 ----------
at_re = re.compile(r'@[^\s|·\n]+')
for q, fn in [('鲁迅说','douyin_鲁迅说_raw.jsonl'), ('故事新编鲁迅','douyin_故事新编鲁迅_raw.jsonl')]:
    srcp = os.path.join('data','douyin',fn)
    outp = os.path.join(DEL,'抖音', fn.replace('.jsonl','_anon.jsonl'))
    n=0
    with open(os.path.join(BASE,srcp),encoding='utf-8') as f, open(outp,'w',encoding='utf-8') as g:
        for line in f:
            o=json.loads(line)
            o['raw']=at_re.sub('@匿名创作者', o.get('raw',''))
            g.write(json.dumps(o,ensure_ascii=False)+'\n'); n+=1
    print('抖音raw',q,n)
# parsed.csv
cr_map={}
def anon_cr(name):
    name=(name or '').strip()
    if name not in cr_map: cr_map[name]='创作者_%03d'%(len(cr_map)+1)
    return cr_map[name]
srcp=os.path.join(BASE,'data','douyin','douyin_parsed.csv')
outp=os.path.join(DEL,'抖音','douyin_parsed_anon.csv')
with open(srcp,encoding='utf-8-sig',newline='') as f, open(outp,'w',encoding='utf-8-sig',newline='') as g:
    rd=csv.DictReader(f); wl=csv.DictWriter(g,fieldnames=rd.fieldnames); wl.writeheader()
    n=0
    for row in rd:
        if '作者' in row: row['作者']=anon_cr(row['作者'])
        wl.writerow(row); n+=1
print('抖音parsed',n)

# ---------- 微信读书（已递归匿名化）直接复制 ----------
copy(r'data\weread_故事新编_采集_2026-09-12.json',
     os.path.join('微信读书','weread_故事新编_采集_2026-09-12.json'))
print('微信读书 复制完成（官方接口返回，已递归移除userVid/name/avatar）')

# ---------- 汇总统计 ----------
for f in ['summary_stats.json','cross_platform_form.csv','douyin_form_distribution.csv']:
    copy(os.path.join('data','analysis',f), os.path.join('汇总统计',f))
print('\n归集完成 ->', DEL)
for sub in ['B站','豆瓣','抖音','微信读书','汇总统计']:
    fp=os.path.join(DEL,sub)
    print(sub, os.listdir(fp))
