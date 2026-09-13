# -*- coding: utf-8 -*-
"""微信读书官方授权接口采集《故事新编》热门划线+公开点评（2026-09-12 时点）。
密钥仅从环境变量 WEREAD_API_KEY 读取，不落盘、不打印。存储时匿名化（剔除昵称/VID/头像）。"""
import os
import json
import time
import urllib.request

API = 'https://i.weread.qq.com/api/agent/gateway'
KEY = os.environ.get('WEREAD_API_KEY', '').strip()
if not KEY:
    raise SystemExit('WEREAD_API_KEY 未设置')
SKILL_VERSION = '1.0.4'
BOOKS = {'40509933': '故事新编（人民文学社版）', '3300227306': '故事新编（电子书版）'}


def call(api_name, **params):
    body = {'api_name': api_name, 'skill_version': SKILL_VERSION}
    body.update(params)
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'},
    )
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read().decode('utf-8'))
            if j.get('upgrade_info'):
                raise SystemExit('upgrade_info: ' + json.dumps(j['upgrade_info'], ensure_ascii=False))
            if j.get('errcode') not in (None, 0):
                raise RuntimeError(f"{api_name} errcode={j.get('errcode')} msg={j.get('errmsg')}")
            return j
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise last


def anonymize(obj, parent_key=None):
    """递归剔除评论者个人信息：author 下的 name/userVid/avatar，以及任何层级的 userVid/avatar。
    保留书籍作者信息（book.author='鲁迅' 等）。"""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in ('userVid', 'avatar'):
                obj.pop(k, None)
            elif k == 'author' and isinstance(obj[k], dict):
                for p in ('name', 'userVid', 'avatar'):
                    obj[k].pop(p, None)
            elif k == 'name' and parent_key == 'author':
                obj.pop(k, None)
            else:
                anonymize(obj[k], parent_key=k)
    elif isinstance(obj, list):
        for it in obj:
            anonymize(it, parent_key=parent_key)
    return obj


out = {}
for bid, bname in BOOKS.items():
    rec = {'bookId': bid, 'bookName': bname, 'fetched_at': '2026-09-12'}
    # 热门划线（服务端固定前 20 条）
    bb = call('/book/bestbookmarks', bookId=bid, chapterUid=0, synckey=0)
    items = bb.get('items', []) or []
    for it in items:
        it.pop('userVid', None)
        it.pop('bookmarkId', None)
    rec['bestbookmarks'] = {'totalCount': bb.get('totalCount'), 'n': len(items), 'items': items}
    # 公开点评（第一页 20 条，默认全部类型）
    rv = call('/review/list', bookId=bid, reviewListType=0, count=20, maxIdx=0, synckey=0)
    reviews = rv.get('reviews', []) or []
    reviews = [anonymize(r) for r in reviews]
    rec['reviews'] = {
        'reviewsCnt': rv.get('reviewsCnt'), 'recentTotalCnt': rv.get('recentTotalCnt'),
        'hasMore': rv.get('reviewsHasMore'), 'n': len(reviews), 'items': reviews,
    }
    # 划线热度统计（全书各章，无文本，仅人数）—— 用 bestbookmarks 的 chapterUid 遍历太贵，跳过
    out[bid] = rec
    print(f"[{bid}] {bname}: bestbookmarks={rec['bestbookmarks']['n']}条(总{rec['bestbookmarks']['totalCount']}), "
          f"reviews={rec['reviews']['n']}条(总{rec['reviews']['reviewsCnt']}), hasMore={rec['reviews']['hasMore']}")

path = r'F:\文学数字人文阐释实践\故事新编研究案例\第五节《故事新编》数字传播生态的算法规训批判\data\weread_故事新编_采集_2026-09-12.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('saved:', path)
