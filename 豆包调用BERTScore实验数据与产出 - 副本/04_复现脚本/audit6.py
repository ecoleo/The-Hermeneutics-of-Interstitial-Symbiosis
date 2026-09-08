# -*- coding: utf-8 -*-
import json, re, statistics as st
d = json.load(open('candidates.json', encoding='utf-8'))
markers = ['似乎','大约','仿佛','然而','于是','大抵','竟','偏','倒','分明','光景','莫非','何尝']
modern = ['系统','数据','代码','模型','算法','程序','服务器','迭代','赋能','bug','BUG','链路','机制','绩效','KPI']
TAIL = ['风格对照','全文完','设计目的是','附：风格','|---','（全文完）','*（全文完','提示词虽能']
def clen(t): return len(re.findall(r'[一-鿿]', t))
def strip_meta(t):
    # 去开头元信息行（前40字内的【...】对话标记）
    if t.startswith('【'):
        t = t.split('\n',1)[-1]
    cuts = [t.find(m) for m in TAIL if t.find(m) >= 0.5*len(t)]
    return t[:min(cuts)] if cuts else t
for label, fn in (('原始', lambda t:t), ('稳健去元信息', strip_meta)):
    print('===', label)
    for g in ['弱约束','中约束','强约束','参照组']:
        rr, mm = [], []
        for k,t in d.items():
            if not k.startswith(g): continue
            if '阶跃' in k and g in ('强约束','参照组'): continue
            t = fn(t); L = clen(t)
            if L < 300: continue
            rr.append(sum(t.count(w) for w in markers)/L*1000)
            mm.append(sum(t.count(w) for w in modern)/L*1000)
        print('  %s 标记词%.2f  现代词%.2f (n=%d)' % (g, st.mean(rr), st.mean(mm), len(rr)))
# 人类样章与理水不变
refs=json.load(open('refs.json',encoding='utf-8'))
for name in ['样章','理水']:
    t=refs[name]; L=clen(t)
    print(name,'标记词%.2f 现代词%.2f'%(sum(t.count(w) for w in markers)/L*1000, sum(t.count(w) for w in modern)/L*1000))
