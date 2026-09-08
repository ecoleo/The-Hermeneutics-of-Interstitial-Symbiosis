# -*- coding: utf-8 -*-
import json, re
cand = json.load(open('candidates.json', encoding='utf-8'))
def show(k, a=0, b=900):
    t = cand[k]
    print('='*15, k, 'len=%d' % len(t)); print(t[a:b]); print()
def ctx(k, w, n=60):
    t = cand[k]
    for mt in re.finditer(w, t):
        s=max(0,mt.start()-n); e=min(len(t),mt.end()+n)
        print('  [%s@%d] …%s…' % (w, mt.start(), t[s:e].replace('\n',' ')))
show('中约束|智谱清言', 0, 700)
show('中约束|阶跃星辰', 0, 700)
ctx('中约束|阶跃星辰','办公室'); ctx('中约束|阶跃星辰','模型')
show('强约束|MiniMax', 0, 500)
ctx('强约束|MiniMax','KPI'); ctx('强约束|MiniMax','算法')
show('参照组|讯飞星火', 0, 1200)
ctx('弱约束|DeepSeek','卷')
show('中约束|文心一言', 0, 350)
