#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
douban_report.py — 把分析结果渲染为单文件 HTML 报告（ECharts）

用法
----
  python douban_report.py --stats ./douban_data/stats.json --data-dir ./douban_data --out ./douban_data/report.html

图表依赖 ECharts（CDN）。若运行环境离线，图表区域会提示，但所有数据仍以表格形式完整呈现。
"""

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root{
  --bg:#f6f7f5; --card:#ffffff; --ink:#1f2328; --muted:#6b7280;
  --line:#e5e7eb; --green:#2e963a; --green2:#42bd56; --amber:#e8a33d; --red:#d9534f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
 line-height:1.7;}
.wrap{max-width:1180px;margin:0 auto;padding:32px 24px 64px}
header{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:24px}
h1{font-size:26px;margin:0 0 8px}
.sub{color:var(--muted);font-size:14px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;margin-left:8px;
 background:#eef2ee;color:var(--green);border:1px solid #cfe3d2}
.badge.warn{background:#fdf3e3;color:#a4691a;border-color:#f0dcb8}
h2{font-size:18px;margin:36px 0 14px;padding-left:11px;border-left:4px solid var(--green)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card .k{font-size:12px;color:var(--muted);letter-spacing:.03em}
.card .v{font-size:25px;font-weight:600;margin-top:6px}
.card .u{font-size:12px;color:var(--muted);margin-left:3px;font-weight:400}
.chart{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;height:380px}
.chart.tall{height:460px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
 border-radius:12px;overflow:hidden;font-size:14px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f2f4f2;font-weight:600;color:#374151;font-size:13px}
tr:last-child td{border-bottom:none}
.quote{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--amber);
 border-radius:8px;padding:12px 16px;margin-bottom:10px}
.quote .meta{font-size:12px;color:var(--muted);margin-bottom:5px}
.quote .txt{font-size:14.5px}
.note{background:#fffdf6;border:1px solid #f0e2c0;border-radius:10px;padding:14px 18px;font-size:13.5px;color:#5c4a2a}
.note ol{margin:8px 0 0 18px;padding:0}
.note li{margin:5px 0}
.fallback{display:none;padding:40px;text-align:center;color:var(--muted);font-size:14px}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>__TITLE__ <span class="badge" id="covbadge">__COVBADGE__</span></h1>
  <div class="sub">__SUB__</div>
</header>

<div class="note" id="caveat">
  <strong>读图前须知</strong>
  <ol>
    <li>本报告样本为豆瓣「__STATUS__」短评中<strong>实际可抓取的部分</strong>（__N__ / __TOTAL__，覆盖率 __COV__）。豆瓣对短评列表设有访问深度限制，未登录态通常仅可达前 ~180 条，登录态可达更深但不保证全量。</li>
    <li>样本<strong>非随机</strong>：列表按「热门」（有用数）或「时间」排序，高赞短评天然被过度代表。因此<em>均分、占比等指标应理解为「可见样本的描述统计」，不宜直接外推为该书读者总体</em>。</li>
    <li>时间趋势基于样本内评论的发表年份，受上述采样偏差影响，仅可用于观察<em>可见话语的漂移</em>，不等同于真实评价史。</li>
    <li>分词方法：__TOKENIZER__。情感方法：__SENT__。__SENTNOTE__</li>
  </ol>
</div>

<h2>总体指标</h2>
<div class="grid">__CARDS__</div>

<h2>评分分布</h2>
<div class="chart" id="c_rating"></div>

<h2>评价随时间的漂移（按年）</h2>
<div class="chart tall" id="c_trend"></div>

<h2>高频关键词（TF-IDF 加权 Top __TOPK__）</h2>
<div class="chart tall" id="c_kw"></div>

<h2>高分（4–5★）与低分（1–2★）特征词对比</h2>
<div class="chart tall" id="c_polar"></div>
<table><thead><tr><th style="width:25%">高分特征词</th><th style="width:25%">词频</th><th style="width:25%">低分特征词</th><th style="width:25%">词频</th></tr></thead><tbody>__POLARROWS__</tbody></table>

<h2>短评长度分布</h2>
<div class="chart" id="c_len"></div>

<h2>分时段关键词（接受史视角）</h2>
<table><thead><tr><th style="width:18%">时段</th><th style="width:10%">评论数</th><th>Top 关键词</th></tr></thead><tbody>__YKWROWS__</tbody></table>

<h2>高赞短评 Top 10</h2>
<div id="quotes">__QUOTES__</div>

<h2>逐年明细</h2>
<table><thead><tr><th>年份</th><th>评论数</th><th>均分</th><th>平均字数</th><th>平均有用数</th></tr></thead><tbody>__YEARROWS__</tbody></table>

<footer>
  数据来源：豆瓣读书短评（__URL__）　·　采集时间：__FETCHED__　·　报告生成：__GEN__<br>
  本工具仅用于个人研究与教学目的的小规模采集，遵守请求间隔限制；数据版权归原平台与用户所有，引用请注明来源。
</footer>
</div>

<script>
var D = __DATA__;
function hasEcharts(){return typeof echarts !== 'undefined';}
function mount(id, opt){
  if(!hasEcharts()){document.getElementById(id).innerHTML='<div class="fallback" style="display:block">图表需联网加载 ECharts；完整数据见下方表格。</div>';return;}
  var el=document.getElementById(id); var ch=echarts.init(el); ch.setOption(opt);
  window.addEventListener('resize',function(){ch.resize();});
}
if(hasEcharts()){
  mount('c_rating',{
    tooltip:{trigger:'axis'},
    grid:{left:50,right:24,top:34,bottom:34},
    xAxis:{type:'category',data:D.rating.labels,name:'星级'},
    yAxis:{type:'value',name:'条数'},
    series:[{type:'bar',data:D.rating.counts,barWidth:'52%',
      itemStyle:{color:function(p){var cs=['#d9534f','#e8a33d','#f0c419','#8bbf4a','#2e963a'];return cs[p.dataIndex]||'#2e963a';},borderRadius:[5,5,0,0]},
      label:{show:true,position:'top',formatter:'{c}'}}]
  });
  mount('c_trend',{
    tooltip:{trigger:'axis'},
    legend:{data:['评论数','均分'],top:0},
    grid:{left:56,right:56,top:42,bottom:44},
    xAxis:{type:'category',data:D.trend.years},
    yAxis:[{type:'value',name:'评论数'},{type:'value',name:'均分',min:function(v){return Math.max(0,Math.floor(v.min*2)/2-0.5)},max:5}],
    series:[
      {name:'评论数',type:'bar',data:D.trend.counts,itemStyle:{color:'#bcd9c2',borderRadius:[4,4,0,0]}},
      {name:'均分',type:'line',yAxisIndex:1,data:D.trend.means,smooth:true,
       symbolSize:6,lineStyle:{width:2.5,color:'#2e963a'},itemStyle:{color:'#2e963a'},
       connectNulls:true}
    ]
  });
  mount('c_kw',{
    tooltip:{trigger:'axis'},
    grid:{left:110,right:60,top:16,bottom:24},
    xAxis:{type:'value'},
    yAxis:{type:'category',data:D.kw.words.slice().reverse(),axisLabel:{fontSize:12}},
    series:[{type:'bar',data:D.kw.freq.slice().reverse(),
      itemStyle:{color:'#42bd56',borderRadius:[0,4,4,0]},
      label:{show:true,position:'right',fontSize:11,color:'#6b7280'}}]
  });
  mount('c_polar',{
    tooltip:{trigger:'axis'},
    legend:{data:['高分(4–5★)','低分(1–2★)'],top:0},
    grid:{left:110,right:60,top:36,bottom:24},
    xAxis:{type:'value'},
    yAxis:{type:'category',data:D.polar.axis},
    series:[
      {name:'高分(4–5★)',type:'bar',data:D.polar.high,itemStyle:{color:'#2e963a',borderRadius:[0,4,4,0]}},
      {name:'低分(1–2★)',type:'bar',data:D.polar.low,itemStyle:{color:'#d9534f',borderRadius:[0,4,4,0]}}
    ]
  });
  mount('c_len',{
    tooltip:{trigger:'axis'},
    grid:{left:50,right:24,top:34,bottom:34},
    xAxis:{type:'category',data:D.len.labels,name:'字数'},
    yAxis:{type:'value',name:'条数'},
    series:[{type:'bar',data:D.len.counts,barWidth:'55%',
      itemStyle:{color:'#7fb2e5',borderRadius:[5,5,0,0]},label:{show:true,position:'top'}}]
  });
}else{
  ['c_rating','c_trend','c_kw','c_polar','c_len'].forEach(function(id){
    document.getElementById(id).innerHTML='<div class="fallback" style="display:block">图表需联网加载 ECharts；完整数据见下方表格。</div>';
  });
}
</script>
</body>
</html>
"""


def read_csv(path):
    import csv
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.reader(f))[1:]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build(stats_path, data_dir, out_path):
    stats = json.load(open(stats_path, "r", encoding="utf-8"))
    d = lambda fn: os.path.join(data_dir, fn)

    rd = read_csv(d("rating_distribution.csv"))
    yr = read_csv(d("yearly_trend.csv"))
    kw = read_csv(d("keywords_top.csv"))
    pol = read_csv(d("keywords_by_rating.csv"))
    ln = read_csv(d("length_distribution.csv"))
    ykw = read_csv(d("yearly_keywords.csv"))
    top = read_csv(d("top_comments.csv"))

    # 数据
    rating_labels, rating_counts = [], []
    for r in rd:
        star = r[0]
        rating_labels.append("无评分" if star == "0" else star + "★")
        rating_counts.append(int(r[1]))

    data = {
        "rating": {"labels": rating_labels, "counts": rating_counts},
        "trend": {
            "years": [r[0] for r in yr],
            "counts": [int(r[1]) for r in yr],
            "means": [float(r[2]) if r[2] not in ("", None) else None for r in yr],
        },
        "kw": {
            "words": [r[0] for r in kw][: int(len(kw)) ],
            "freq": [int(r[1]) if str(r[1]).isdigit() else 0 for r in kw],
        },
        "polar": {
            "axis": [r[0] for r in pol if r[0]],
            "high": [int(r[1]) for r in pol if r[0]],
            "low": [int(r[3]) for r in pol if r[2]],
        },
        "len": {"labels": [r[0] for r in ln], "counts": [int(r[1]) for r in ln]},
    }
    # polar 两列长度可能不同，取交集前 12
    n = 12
    data["polar"]["axis"] = data["polar"]["axis"][:n]
    data["polar"]["high"] = data["polar"]["high"][:n]
    data["polar"]["low"] = data["polar"]["low"][:n]

    # 卡片
    cards = [
        ("样本量", stats.get("n_comments"), "条"),
        ("均分", stats.get("rating_mean"), "★"),
        ("标准差", stats.get("rating_stdev"), ""),
        ("五星占比", stats.get("pct_5star"), "%"),
        ("低分占比(1–2★)", stats.get("pct_low_1_2star"), "%"),
        ("极化度(熵)", stats.get("rating_polarization_entropy"), ""),
        ("平均字数", stats.get("text_len_mean"), "字"),
        ("平均有用数", stats.get("votes_mean"), ""),
        ("年份跨度", f'{stats.get("year_min") or "?"}–{stats.get("year_max") or "?"}', ""),
    ]
    card_html = "".join(
        f'<div class="card"><div class="k">{esc(k)}</div><div class="v">{esc(v)}'
        f'<span class="u">{esc(u)}</span></div></div>'
        for k, v, u in cards
    )

    cov = stats.get("coverage")
    cov_txt = f"{cov*100:.2f}%" if cov else "未知"
    covbadge = f"覆盖率 {cov_txt}"
    badge_cls = "badge warn" if (cov is None or cov < 0.2) else "badge"
    total = stats.get("declared_total") or "未知"

    polar_rows = "".join(
        f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td><td>{esc(r[3])}</td></tr>"
        for r in pol
    )
    ykw_rows = "".join(f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td></tr>" for r in ykw)
    year_rows = "".join(
        f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{esc(r[2])}</td><td>{esc(r[3])}</td><td>{esc(r[4])}</td></tr>"
        for r in yr
    )
    quotes = "".join(
        f'<div class="quote"><div class="meta">{esc(r[0])} 人认为有用 · {esc(r[1])}★ · '
        f'{esc(r[2])} · {esc(r[3])}</div><div class="txt">{esc(r[4])}</div></div>'
        for r in top[:10]
    )

    sent = stats.get("sentiment_method", "off")
    sentnote = ("（情感为启发式结果，仅作辅助，须与星级交叉验证，不得单独作为结论）"
                if sent != "off" else "（本次未启用情感分析，以星级作为评价倾向代理）")

    html = (TPL
            .replace("__TITLE__", esc(stats.get("book") or "豆瓣短评分析"))
            .replace("__SUB__", esc(f'豆瓣读书 #{stats.get("subject_id")} · '
                                    f'{stats.get("status_label", "")}短评 · '
                                    f'样本 {stats.get("n_comments")} 条'))
            .replace("__COVBADGE__", esc(covbadge))
            .replace("__STATUS__", esc(stats.get("status_label", "")))
            .replace("__N__", esc(stats.get("n_comments")))
            .replace("__TOTAL__", esc(total))
            .replace("__COV__", esc(cov_txt))
            .replace("__TOKENIZER__", esc(stats.get("tokenizer", "")))
            .replace("__SENT__", esc(sent))
            .replace("__SENTNOTE__", sentnote)
            .replace("__CARDS__", card_html)
            .replace("__TOPK__", str(len(kw)))
            .replace("__POLARROWS__", polar_rows)
            .replace("__YKWROWS__", ykw_rows)
            .replace("__YEARROWS__", year_rows)
            .replace("__QUOTES__", quotes)
            .replace("__URL__", esc(f'https://book.douban.com/subject/{stats.get("subject_id")}/comments/'))
            .replace("__FETCHED__", esc(stats.get("generated_at", "")))
            .replace("__GEN__", esc(stats.get("generated_at", "")))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            )
    # badge class 修正
    html = html.replace('<span class="badge" id="covbadge">',
                        f'<span class="{badge_cls}" id="covbadge">')

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成：{out_path}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="生成豆瓣短评可视化 HTML 报告")
    ap.add_argument("--stats", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    out = a.out or os.path.join(a.data_dir, "report.html")
    build(a.stats, a.data_dir, out)


if __name__ == "__main__":
    main()
