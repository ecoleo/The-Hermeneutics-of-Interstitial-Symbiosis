# -*- coding: utf-8 -*-
import json, re, csv, statistics as st
cand = json.load(open('candidates.json', encoding='utf-8'))
rows = list(csv.DictReader(open('bertscore_full.csv', encoding='utf-8-sig')))

print('========== 1. 现代技术/治理词逐篇计数 ==========')
words = ['系统','数据','代码','bug','程序','模型','迭代','日志','链路','KPI','敏捷','办公室','算法','参数','项目','效率','优化','版本','接口','bug','故障']
groups = ['弱约束','中约束','强约束','参照组']
models = ["通义千问","文心一言","DeepSeek","Kimi","智谱清言","豆包","腾讯元宝","讯飞星火","MiniMax","阶跃星辰"]
for g in groups:
    print('----', g)
    for m in models:
        t = cand.get(g+'|'+m, '')
        if not t or '无法生成' in t[:30]:
            print('  %-6s [未生成]' % m); continue
        hits = {w: len(re.findall(w, t, flags=re.I)) for w in words}
        hits = {k:v for k,v in hits.items() if v}
        print('  %-6s 字数%d %s' % (m, len(t), hits))

print()
print('========== 2. 修订稿引文逐条验证（应全部 True） ==========')
quotes = [
 ('弱约束|智谱清言','大约并不比某人长了六个指头'),
 ('弱约束|智谱清言','《理水》之外'),
 ('弱约束|腾讯元宝','考据确凿'),
 ('弱约束|腾讯元宝','大约不至于错'),
 ('弱约束|MiniMax','仿鲁迅《故事新编》体'),
 ('弱约束|DeepSeek','卷'),
 ('中约束|智谱清言','汤汤洪水方割'),
 ('中约束|智谱清言','上古结绳而治'),
 ('中约束|文心一言','文化山'),
 ('中约束|Kimi','若昔者'),
 ('中约束|Kimi','轩辕氏之世'),
 ('中约束|阶跃星辰','结绳而治'),
 ('中约束|阶跃星辰','民无奸宄'),
 ('强约束|DeepSeek','代码'),
 ('强约束|DeepSeek','比您的字快得多'),
 ('强约束|DeepSeek','办公室'),
 ('参照组|通义千问','系统'),
 ('参照组|通义千问','bug'),
 ('参照组|通义千问','日志'),
 ('参照组|通义千问','冗余数据'),
 ('参照组|DeepSeek','似是而非'),
 ('参照组|DeepSeek','不类文理'),
 ('参照组|DeepSeek','全是错的'),
 ('参照组|Kimi','复核'),
 ('参照组|智谱清言','官职'),
 ('参照组|智谱清言','认得官'),
 ('参照组|智谱清言','喂数据'),
 ('参照组|智谱清言','管理链路'),
 ('参照组|文心一言','迭代模型'),
 ('参照组|Kimi','训练数据'),
]
for k, q in quotes:
    t = cand.get(k, '')
    print(('OK ' if q in t else '** MISSING ** '), k, '::', q)

print()
print('========== 3. 每模型四组对样章F1 + 是否参照组最高 ==========')
by = {}
for r in rows:
    by.setdefault(r['模型'], {})[r['组']] = float(r['F1_样章'])
for m in models:
    d = by[m]
    mx = max(d.values()); ref = d.get('参照组')
    flag = '参照最高' if ref is not None and abs(ref-mx) < 1e-9 else ('参照非最高->%s' % max(d,key=d.get))
    print('%-6s 弱%.3f 中%.3f 强%s 参%s | %s' % (m, d.get('弱约束',-1), d.get('中约束',-1),
          ('%.3f'%d['强约束']) if '强约束' in d else 'NA',
          ('%.3f'%d['参照组']) if '参照组' in d else 'NA', flag))

print()
print('========== 4. 跨组均值排名（对样章/对原作） ==========')
for key in ['F1_样章','F1_原作']:
    avg = {}
    for m in models:
        vals = [float(r[key]) for r in rows if r['模型']==m]
        avg[m] = sum(vals)/len(vals)
    rank = sorted(avg.items(), key=lambda x:-x[1])
    print(key)
    for i,(m,v) in enumerate(rank,1): print('  %2d. %-6s %.4f (n=%d)' % (i,m,v,len([r for r in rows if r['模型']==m])))

print()
print('========== 5. 参照组较强大组提升幅度（对样章） ==========')
for m in models:
    d = by[m]
    if '参照组' in d and '强约束' in d:
        print('  %-6s 强%.3f->参%.3f 提升%+.3f' % (m,d['强约束'],d['参照组'],d['参照组']-d['强约束']))

print()
print('========== 6. 中约束去离群后均值 ==========')
for key in ['F1_原作','F1_样章']:
    allv=[float(r[key]) for r in rows if r['组']=='中约束']
    keep=[float(r[key]) for r in rows if r['组']=='中约束' and r['模型'] not in ('Kimi','阶跃星辰')]
    print(key,'全组%.4f(n10) 去两离群%.4f(n8)'%(st.mean(allv),st.mean(keep)))
