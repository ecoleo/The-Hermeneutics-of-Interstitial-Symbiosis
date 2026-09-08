# -*- coding: utf-8 -*-
"""把维基文库 wikitext 清洗为纯文本并繁转简；清洗样章文本。"""
import os, re, json
from opencc import OpenCC
cc = OpenCC('tw2s')

def wiki_to_text(wt):
    # 先移除跨多行的 {{header ...}} 模板块
    wt = re.sub(r'\{\{[Hh]eader.*?\}\}', '', wt, flags=re.S)
    lines = wt.splitlines()
    out = []
    skip = False
    for ln in lines:
        s = ln.strip()
        if not s: continue
        if s.startswith('{{') and s.endswith('}}'): continue
        if s.startswith('=='):  # 章节标题 一、二…
            s = re.sub(r'=+', '', s).strip()
            if re.fullmatch(r'[一二三四五六七八九十0-9]+', s): continue
        # 去模板
        s = re.sub(r'\{\{[^{}]*\}\}', '', s)
        # 去wiki链接保留文字
        s = re.sub(r'\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]', r'\1', s)
        s = re.sub(r"'''?", '', s)
        s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
        s = re.sub(r'<[^>]+>', '', s)
        s = s.replace('[[','').replace(']]','')
        if s.strip(): out.append(s.strip())
    txt = '\n'.join(out)
    txt = cc.convert(txt)
    return txt

refs = {}
for f in sorted(os.listdir('luxun')):
    if f.endswith('.wiki'):
        name = f[:-5]
        wt = open(f'luxun/{f}',encoding='utf-8').read()
        t = wiki_to_text(wt)
        refs[name] = t
        print(name, len(t), '| head:', t[:40].replace('\n',' '))

# 样章（PDF抽取后字间有空格）
yz = open('yangzhang.txt',encoding='utf-8').read()
# 去页码行与说明
yz_lines = []
for ln in yz.splitlines():
    s = ln.strip()
    if not s: continue
    if s.startswith('===== PAGE'): continue
    if s.startswith('三、样章') or s.startswith('造  字') or s.startswith('故事新编'): continue
    if s.startswith('※'): continue
    yz_lines.append(s)
yz_txt = ''.join(yz_lines)
# PDF抽取中文字间夹空格：去掉中文字符之间的空格
yz_txt = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff，。、；：？！“”‘’（）《》—…·\-])', '', yz_txt)
yz_txt = re.sub(r'\s+', '', yz_txt)  # 中文文本内部空格全部去除
# 截断样章正文之后的设计说明（"以上为《造字》试写片段"等）
for marker in ['以上为', '五则候选', '拟续写', '苦是一样的苦。']:
    pos = yz_txt.find(marker)
    if pos > 500:
        yz_txt = yz_txt[:pos + (len(marker) if marker == '苦是一样的苦。' else 0)]
        if marker == '苦是一样的苦。': break
refs['样章'] = yz_txt.strip('※ ').strip()
print('样章', len(yz_txt), '| head:', yz_txt[:60])

json.dump(refs, open('refs.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved refs.json; stories:', [k for k in refs if k!='样章'])
