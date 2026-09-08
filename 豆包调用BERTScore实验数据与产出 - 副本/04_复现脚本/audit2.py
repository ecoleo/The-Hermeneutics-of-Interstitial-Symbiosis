# -*- coding: utf-8 -*-
import json
cand = json.load(open('candidates.json', encoding='utf-8'))

def show(k, head=600, tail=0):
    t = cand[k]
    print('='*20, k, 'len=%d' % len(t))
    print(t[:head])
    if tail: print('...[TAIL]...', t[-tail:])
    print()

# 弱约束全部开篇（完成三路径分类）
for m in ["通义千问","文心一言","DeepSeek","Kimi","智谱清言","豆包","腾讯元宝","讯飞星火","MiniMax","阶跃星辰"]:
    show('弱约束|'+m, head=260)
