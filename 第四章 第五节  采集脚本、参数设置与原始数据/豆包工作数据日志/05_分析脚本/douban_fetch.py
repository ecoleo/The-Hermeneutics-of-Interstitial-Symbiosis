# -*- coding: utf-8 -*-
"""
豆瓣《故事新编》短评采集脚本（按本次实际成功路径固化，纯标准库实现）。
- 对象：subject 2046909，status=P（读过），sort=new_score（热门）/time（最新）各 5 页。
- 鉴权：Cookie 从环境变量 DOUBAN_COOKIE 读取（不硬编码、不写入结果文件）。
  注意：匿名（未登录）状态下 sort=time 会返回 403，必须带登录态 Cookie。
- 限速：默认每请求间隔 18 秒（豆瓣约 200 请求/小时/IP），可用环境变量 DOUBAN_SLEEP 覆盖。
- 输出：data/douban_2046909_auth/comments_2046909_P.jsonl（每行一条，字段见数据说明）。
运行：
  PowerShell: $env:DOUBAN_COOKIE="你的cookie"; python douban_fetch.py
"""
import os, re, json, time, html
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, 'data', 'douban_2046909_auth')
os.makedirs(OUTDIR, exist_ok=True)
SUBJECT = '2046909'
SORTS = ['new_score', 'time']          # 热门 / 最新
PAGES = 5                              # 每排序 5 页，每页 20 条 -> 各 100
SLEEP = float(os.environ.get('DOUBAN_SLEEP', '18'))
COOKIE = os.environ.get('DOUBAN_COOKIE', '')

STAR_TITLE = {'力荐': '5', '推荐': '4', '还行': '3', '较差': '2', '很差': '1'}

class CommentParser(HTMLParser):
    """从一页短评 HTML 中抽取结构化字段（标准库，无第三方依赖）。"""
    def __init__(self):
        super().__init__()
        self.items, self.cur = [], None
        self._flag = None  # 当前正在读取的文本槽位
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '')
        if tag == 'div' and 'comment-item' in cls:
            cid = a.get('data-cid') or (a.get('id', '').replace('li_', ''))
            self.cur = {'cid': cid, 'user': '', 'rating': '', 'rating_title': '',
                        'votes': '', 'time': '', 'location': '', 'text': ''}
        elif self.cur is not None:
            if tag == 'a' and 'comment-info' not in cls and self.cur['user'] == '' and a.get('href', '').startswith('https://www.douban.com/people'):
                self._flag = 'user'
            elif tag == 'span' and 'user-stars' in cls:
                t = a.get('title', '')
                self.cur['rating_title'] = t
                self.cur['rating'] = STAR_TITLE.get(t, '')
            elif tag == 'span' and 'comment-time' in cls:
                t = (a.get('title', '') or '').strip()
                if t:
                    self.cur['time'] = t          # 优先取 title 完整时间，不再重复读文本
                else:
                    self._flag = 'time'           # 无 title 时退化为读元素文本
            elif tag == 'span' and 'votes' in cls:
                self._flag = 'votes'
            elif tag == 'span' and cls == 'short':
                self._flag = 'text'
    def handle_endtag(self, tag):
        if tag == 'div' and self.cur is not None and self._flag is None and self.cur['text']:
            self.items.append(self.cur); self.cur = None
        if self._flag in ('user', 'votes', 'text', 'time'):
            self._flag = None
    def handle_data(self, data):
        if self.cur is not None and self._flag:
            key = {'user':'user','votes':'votes','text':'text','time':'time'}[self._flag]
            self.cur[key] += data.strip()

def fetch(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        'Cookie': COOKIE,
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    with urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')

def main():
    assert COOKIE, '请先设置环境变量 DOUBAN_COOKIE（登录态 Cookie）'
    out = os.path.join(OUTDIR, 'comments_%s_P.jsonl' % SUBJECT)
    n = 0
    with open(out, 'w', encoding='utf-8') as g:
        for sort in SORTS:
            for page in range(PAGES):
                start = page * 20
                url = ('https://book.douban.com/subject/%s/comments/?status=P&sort=%s&start=%d'
                       % (SUBJECT, sort, start))
                htmltext = fetch(url)
                if '403' in htmltext[:500] or 'sec.douban.com' in htmltext:
                    print('被限流/403，已保存进度，稍后重试：', url); return
                p = CommentParser(); p.feed(htmltext)
                for it in p.items:
                    it['_sort'] = sort
                    it['_fetched_at'] = datetime.now().isoformat(timespec='seconds')
                    g.write(json.dumps(it, ensure_ascii=False) + '\n'); n += 1
                print('sort=%s start=%d 本页%d 累计%d' % (sort, start, len(p.items), n))
                time.sleep(SLEEP)
    print('完成，共', n, '条 ->', out)

if __name__ == '__main__':
    main()
