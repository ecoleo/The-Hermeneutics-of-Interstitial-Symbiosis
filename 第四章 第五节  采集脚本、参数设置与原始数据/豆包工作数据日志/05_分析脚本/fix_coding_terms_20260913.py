# -*- coding: utf-8 -*-
"""2026-09-13（二次）：修正编码程序表述——
区分"预登记词典（B站，先验建构）"与"开放编码（抖音，数据驱动归纳后锁定）"，
避免把抖音开放编码误列为"预先登记"。仅改两处文字，增量编辑、继承样式。
"""
import copy
import os

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判'
DST = os.path.join(BASE, '第五节_数字副文本采集与修订交付_20260912', '03_论文修订稿',
                   '第五节 接受-批判进路：《故事新编》数字传播生态的算法规训批判（数字副文本实证修订稿）.docx')

PATCHES = [
    # 方法论说明段
    ('分析采用预先登记、词表冻结于正式计数之前的编码本（B站四类词典、抖音六类开放编码并经两轮人工校准），统计上使用',
     '分析采用两套明确标注的编码程序——B站标签分类为预先登记的四类词典（文学品质、知识教育、有声说书、幽默解构，词元依据研究问题与原稿论题建构、在正式计数前固定），抖音内容形式分类为开放编码（对样本逐条阅读归纳出互斥类别，经两轮人工校准锁定后正式编码）——统计上使用'),
    # 方法段（三）抖音处
    ('并按预先登记、经两轮开放编码校准后锁定的编码本作内容形式分类；',
     '并按开放编码程序（对样本逐条阅读、经两轮人工校准锁定六类互斥类别）作内容形式分类；'),
]


def set_font(run, tmpl_rpr, bold):
    if tmpl_rpr is not None:
        run._element.insert(0, copy.deepcopy(tmpl_rpr))
    run.font.size = None  # 继承模板字号
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.insert(0, rf)
    rf.set(qn('w:ascii'), 'Times New Roman')
    rf.set(qn('w:hAnsi'), 'Times New Roman')
    rf.set(qn('w:eastAsia'), '宋体')


def patch_para(p, old, new):
    if old not in p.text:
        return False
    text = p.text.replace(old, new)
    bold_first = bool(p.runs and p.runs[0].font.bold)
    tmpl = None
    if p.runs and p.runs[0]._element.rPr is not None:
        tmpl = copy.deepcopy(p.runs[0]._element.rPr)
    for r in list(p._element.findall(qn('w:r'))):
        p._element.remove(r)
    if bold_first and '。' in text:
        i = text.index('。') + 1
        r1 = p.add_run(text[:i]); set_font(r1, tmpl, True)
        r2 = p.add_run(text[i:]); set_font(r2, tmpl, False)
    else:
        r = p.add_run(text); set_font(r, tmpl, False)
    return True


d = docx.Document(DST)
done = []
for p in d.paragraphs:
    for old, new in PATCHES:
        if old in p.text:
            ok = patch_para(p, old, new)
            done.append((ok, p.text[:24]))
            break  # 一段只处理一处

print('修补结果:')
for ok, head in done:
    print(' ', 'OK ' if ok else 'FAIL', head)

d.save(DST)
print('已保存:', DST)

d2 = docx.Document(DST)
full = '\n'.join(p.text for p in d2.paragraphs)
print('回读段落数:', len(d2.paragraphs), '图片:', len(d2.inline_shapes))
print('旧表述残留:',
      any(old in full for old, _ in PATCHES))
print('新表述在文:',
      all(new in full for _, new in PATCHES))
