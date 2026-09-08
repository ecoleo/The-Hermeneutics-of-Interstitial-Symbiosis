# -*- coding: utf-8 -*-
import json, re, statistics as st
d=json.load(open('candidates.json',encoding='utf-8'))
GROUPS=['弱约束','中约束','强约束','参照组']
# 鲁迅式标记词（揣测语气/转折/反讽副词）
markers=['似乎','大约','仿佛','然而','于是','大抵','竟','偏','倒','分明','光景','莫非','何尝']
modern=['系统','数据','代码','模型','算法','程序','服务器','迭代','赋能','bug','BUG','链路','机制','绩效','KPI']
def clean_len(t): return len(re.findall(r'[一-鿿]',t))
out={}
for g in GROUPS:
    rates=[]; mr=[]
    for k,t in d.items():
        if not k.startswith(g): continue
        if '阶跃' in k and g in ('强约束','参照组'): continue
        L=clean_len(t)
        if L<300: continue
        cnt=sum(t.count(w) for w in markers)
        rates.append(cnt/L*1000)
        mc=sum(t.count(w) for w in modern)
        mr.append(mc/L*1000)
    out[g]=(round(st.mean(rates),2),[round(x,2) for x in rates],round(st.mean(mr),2))
    print(g,'鲁迅标记词/千字 均值=',round(st.mean(rates),2),'范围',round(min(rates),2),'-',round(max(rates),2),
          '| 现代技术词/千字=',round(st.mean(mr),2))
# 人类样章基准
refs=json.load(open('refs.json',encoding='utf-8'))
yz=refs['样章']; L=clean_len(yz)
print('人类样章 鲁迅标记词/千字=',round(sum(yz.count(w) for w in markers)/L*1000,2),
      '现代技术词/千字=',round(sum(yz.count(w) for w in modern)/L*1000,2))
lux=refs['理水']; L2=clean_len(lux)
print('鲁迅《理水》标记词/千字=',round(sum(lux.count(w) for w in markers)/L2*1000,2))
