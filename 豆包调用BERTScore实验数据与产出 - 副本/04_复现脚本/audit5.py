# -*- coding: utf-8 -*-
import json, re, statistics as st
d = json.load(open('candidates.json', encoding='utf-8'))
markers = ['似乎','大约','仿佛','然而','于是','大抵','竟','偏','倒','分明','光景','莫非','何尝']
modern = ['系统','数据','代码','模型','算法','程序','服务器','迭代','赋能','bug','BUG','链路','机制','绩效','KPI']
META = ['风格对照','全文完','【WorkBuddy','【和文心','设计目的是','附：','|---','（全文完）','*（全文完']
def clen(t): return len(re.findall(r'[一-鿿]', t))
def strip_meta(t):
    cuts = [t.find(m) for m in META if t.find(m) >= 0]
    return t[:min(cuts)] if cuts else t
print('=== 元信息尾部长度占比 ===')
for k,t in d.items():
    if '无法生成' in t[:30]: continue
    s = strip_meta(t)
    if len(s) < len(t)-20:
        print('%-14s 原文%d 清洗后%d 截去%d字 (%.0f%%)' % (k, len(t), len(s), len(t)-len(s), 100*(len(t)-len(s))/len(t)))
print()
for label, fn in (('原始', lambda t:t), ('去元信息', strip_meta)):
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
        print('  %s 标记词%.2f  现代词%.2f' % (g, st.mean(rr), st.mean(mm)))
