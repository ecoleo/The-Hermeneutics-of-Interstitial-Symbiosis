# -*- coding: utf-8 -*-
"""解析抖音浏览器采集的原始卡片文本为结构化字段，并按【预先登记】规则编码内容形式。
原始格式: "形式或时长 | 点赞数 | 标题(含#标签) | @作者 | · 发布时间"
"""
import csv
import json
import os
import re
from collections import Counter

BASE = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判'
SRC = {
    '鲁迅说': os.path.join(BASE, 'data', 'douyin', 'douyin_鲁迅说_raw.jsonl'),
    '故事新编 鲁迅': os.path.join(BASE, 'data', 'douyin', 'douyin_故事新编鲁迅_raw.jsonl'),
}

# 内容形式编码本（经两轮开放编码校准后锁定；互斥主类别按下列优先级判定）
# 编码流程：演绎 > 讲解 > 玩梗 > 名句呈现 > 共鸣纪念 > 其他
FORM_RULES = [
    ('剧情演绎类', ['短剧', '演绎', '漫剧', '情景剧', '独白剧', '演出来', '翻拍', '特别演出']),
    ('知识讲解类', ['解读', '赏析', '书评', '带你读', '带你理解', '带你看', '深度', '理解',
                  '讲透', '讲述', '共读', '阅读', '书单', '文脉', '参考篇目', '三分钟',
                  '聊聊', '谈谈', '解析', '品读', '导读', '讲解', '知识', '文学课',
                  '诞生', '思想内容', '带你走过', '教授', '为何', '为什么', '如何',
                  '误读', '女性观', '答案', '自我反省', '五篇文章', '好读', '脑洞',
                  '这本书', '晚年之作', '30年代文学', '作文', '补天', '奔月', '铸剑',
                  '采薇', '理水', '出关', '非攻', '神话', '典故', '短篇', '传世',
                  '小说作品', '改编传统', '框架', '深邃', '劲健']),
    ('仿写玩梗类', ['用鲁迅', '鲁迅体', '大抵', '仿写', '鲁迅的口吻', '鲁迅的话怎么说',
                  '鲁迅没说', '鲁迅：', '鲁迅说:', '鲁迅说：', '口吻', 'emo文案',
                  '没钱', '我累了', '我饿了', '我冻死', '表白', '年终总结', '说过',
                  '深入骨髓的穷', '懂鲁迅的朋友', '倒也不是', '优雅地告诉你',
                  '鲁迅先生说了', '鲁迅先生说过', '听鲁迅', '鲁迅先生的话', '鲁讯']),
    ('名句呈现类', ['语录', '名言', '金句', '十大', '句话', '毒舌', '扎心', '顶级讽刺',
                  '猛兽', '书摘', '摘抄']),
    ('共鸣纪念类', ['纪念', '读懂', '讨论太多', '叫醒', '装睡', '脊梁', '觉醒', '麻木',
                  '通透', '血淋淋', '震撼心灵', '一生', '战士', '清醒', '文章', '冷涩',
                  '人间清醒']),
]
# 名句呈现：直接以鲁迅原文为内容主体（经典原句特征词 / 标题被引号包裹）
QUOTE_MARKERS = ['摆脱冷气', '炬火', '横眉冷对', '本没有路', '走的人多了', '从来如此',
                 '铁屋', '俯首甘为', '愿中国青年', '唯一的光', '不必等候', '向上走',
                 '精神界的战士', '振聋发聩', '以笔为刃', '猛兽', '便对', '题辞']
QUOTE_BRACKETS = ['“', '”', '"', '「', '」', '《']
# 与鲁迅/《故事新编》无关的混入内容判定词（任一命中即视为相关，否则标记无关混入）
RELEVANCE_MARKERS = ['鲁迅', '周树人', '鲁讯', '迅哥', '故事新编', '补天', '奔月', '铸剑',
                     '采薇', '理水', '出关', '非攻', '狂人', '阿q', '阿Q', '呐喊',
                     '野草', '热风', '坟', '朝花夕拾', '杂文', '女娲', '眉间尺']
FORM_ORDER = ['剧情演绎类', '知识讲解类', '仿写玩梗类', '名句呈现类', '共鸣纪念类',
              '无关混入', '其他']


def parse_likes(s):
    s = (s or '').strip()
    if not s:
        return None
    m = re.match(r'^([\d.]+)\s*万$', s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.match(r'^([\d.]+)\s*亿$', s)
    if m:
        return int(float(m.group(1)) * 100000000)
    m = re.match(r'^(\d+)$', s)
    if m:
        return int(m.group(1))
    return None


def parse_duration(s):
    """返回秒；图文返回 None。"""
    s = (s or '').strip()
    if s == '图文':
        return None
    if re.match(r'^\d{1,2}(:\d{2})+$', s):
        parts = [int(x) for x in s.split(':')]
        sec = 0
        for p in parts:
            sec = sec * 60 + p
        return sec
    return None


def encode_form(title, is_image, tags=''):
    hits = []
    blob = (title + ' ' + tags).strip()
    for cat, kws in FORM_RULES:
        matched = [k for k in kws if k in blob]
        if matched:
            hits.append(cat)
    main = hits[0] if hits else None
    if main is None:
        if any(m in title for m in QUOTE_MARKERS) or any(b in title for b in QUOTE_BRACKETS):
            main = '名句呈现类'
            hits.append('名句呈现类(原句特征)')
        elif is_image:
            main = '名句呈现类'
            hits.append('名句呈现类(图文推定)')
        else:
            main = '其他'
    # 相关性：仿写玩梗（拟鲁迅体）本身即相关；其余需标题/标签含鲁迅相关词
    if main != '仿写玩梗类' and not any(m in blob for m in RELEVANCE_MARKERS):
        main = '无关混入'
        hits.append('无关混入(无鲁迅相关词)')
    if not title.strip() and main == '其他':
        hits.append('其他(标题缺失)')
    return main, hits


def parse_row(query, raw):
    parts = [p.strip() for p in raw.split(' | ')]
    form_field = parts[0] if parts else ''
    likes_field = parts[1] if len(parts) > 1 else ''
    time_field = parts[-1] if parts[-1].startswith('·') else ''
    if time_field:
        parts = parts[:-1]
    author = ''
    if parts and parts[-1].startswith('@'):
        author = parts[-1][1:]
        parts = parts[:-1]
    title = ' '.join(parts[2:]) if len(parts) > 2 else ''
    is_image = form_field == '图文'
    duration = parse_duration(form_field)
    tags = re.findall(r'#([^\s#@]+)', title)
    title_clean = re.sub(r'#[^\s#@]+', '', title).strip()
    main_form, all_hits = encode_form(title_clean, is_image, ';'.join(tags))
    return {
        'query': query,
        '载体形式': '图文' if is_image else '视频',
        '时长秒': duration if duration is not None else '',
        '点赞数': parse_likes(likes_field),
        '标题': title_clean[:200],
        '话题标签': ';'.join(tags),
        '作者': author,
        '发布时间': time_field.lstrip('· ').strip(),
        '内容形式主类': main_form,
        '编码命中': ';'.join(all_hits),
    }


def main():
    rows = []
    for q, path in SRC.items():
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append(parse_row(q, obj['raw']))
    out_csv = os.path.join(BASE, 'data', 'douyin', 'douyin_parsed.csv')
    fields = ['query', '载体形式', '时长秒', '点赞数', '内容形式主类', '标题',
              '话题标签', '作者', '发布时间', '编码命中']
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print('总条数:', len(rows), '->', out_csv)

    for q in SRC:
        sub = [r for r in rows if r['query'] == q]
        print('\n=== query=%s, n=%d ===' % (q, len(sub)))
        c = Counter(r['内容形式主类'] for r in sub)
        for cat in FORM_ORDER:
            print('  %s: %d (%.1f%%)' % (cat, c[cat], c[cat] / len(sub) * 100 if sub else 0))
        img = sum(1 for r in sub if r['载体形式'] == '图文')
        print('  图文 %d / 视频 %d' % (img, len(sub) - img))
        tagc = Counter(t for r in sub for t in r['话题标签'].split(';') if t)
        print('  高频话题标签 Top12:', tagc.most_common(12))


if __name__ == '__main__':
    main()
