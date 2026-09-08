# -*- coding: utf-8 -*-
import json
cand = json.load(open('candidates.json', encoding='utf-8'))
checks = [
 ('强约束|DeepSeek','仓颉正在办公室里打盹'),
 ('强约束|DeepSeek','听说他们用一种什么'),
 ('参照组|Kimi','龟甲所读'),
 ('参照组|Kimi','复核复核者'),
 ('参照组|智谱清言','把问题做成了官职'),
 ('参照组|智谱清言','认得官'),
 ('参照组|DeepSeek','似是而非，不类文理'),
 ('参照组|DeepSeek','全是错的，但你们不知道自己错了'),
 ('参照组|通义千问','四个未闭的bug'),
 ('参照组|通义千问','造系统'),
 ('弱约束|Kimi','错也错得整齐些'),
 ('强约束|MiniMax','您已被优化了'),
 ('强约束|MiniMax','PPT'),
 ('中约束|阶跃星辰','结绳文化传承推进办公室'),
 ('中约束|智谱清言','绳安'),
 ('中约束|智谱清言','国粹'),
 ('中约束|文心一言','鸟头先生'),
]
for k,q in checks:
    t=cand.get(k,'')
    print(('OK ' if q in t else '** MISS **'), k, '::', q)
print()
# 打印 Kimi参照 复核链原文、智谱参照官职段原文、通义参照bug段
import re
def around(k,q,n=120):
    t=cand[k]; i=t.find(q)
    print('---',k); print(t[max(0,i-n):i+n+len(q)].replace('\n',' ')); print()
around('参照组|Kimi','复核')
around('参照组|智谱清言','官职')
around('参照组|通义千问','bug')
around('强约束|DeepSeek','办公室')
