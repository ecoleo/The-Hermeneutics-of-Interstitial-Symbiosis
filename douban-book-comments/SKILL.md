---
name: douban-book-comments
description: 抓取豆瓣读书指定图书「读过/想读/在读」分类下的短评，做量化分析并生成可视化 HTML 报告。用于文学接受研究、读者评价分析、舆情与口碑量化。当用户提到「豆瓣短评」「豆瓣评分」「读过的人怎么评价」「抓取豆瓣评论」「读者接受分析」等需求时使用。
agent_created: true
---

# 豆瓣读书短评采集 · 量化分析 · 可视化

把「这本书读过的人怎么说」变成可核验的数据：采集 → 量化 → 出图 → 出报告。

## 快速开始

```bash
# 1. 查条目 ID（一本书有多个版本，必须选对）
python scripts/douban_fetch.py --query 故事新编

# 2. 采集「读过」短评（默认热门+最新双排序合并去重）
python scripts/douban_fetch.py --id 2046909 --out ./douban_data

# 3. 量化分析
python scripts/douban_analyze.py --input ./douban_data/comments_2046909_P.jsonl --out ./douban_data

# 4. 生成可视化报告
python scripts/douban_report.py --stats ./douban_data/stats.json \
    --data-dir ./douban_data --out ./douban_data/report.html
```

Windows 下若中文输出乱码，先执行 `chcp 65001` 或 `set PYTHONIOENCODING=utf-8`。
Python 用托管版本：`C:\Users\HUAWEI\.workbuddy\binaries\python\versions\3.13.12\python.exe`。

## 关键限制：先说清楚，别自欺欺人

**「全部短评」在技术上通常拿不到。** 这一点必须在任何报告和结论中如实披露：

| 条件 | 可达深度（实测） | 备注 |
|---|---|---|
| 未登录 | 约 **180 条**（start=0…160，第 180 起返回 403） | 每页 20 条 |
| 带 Cookie 登录态 | 显著提高，但不保证全量 | 仍可能遇验证码/临时封禁 |

例如鲁迅《故事新编》（#2046909）读过短评声明共 **8791 条**，未登录能取约 180 条，
覆盖率约 2%。脚本会把「抓取数 / 声明总数 / 覆盖率」写进 `meta.json` 和 `stats.json`，
并在 HTML 报告顶部以醒目提示呈现。

**更重要的是样本偏差**：列表只会按「热门（有用数）」或「时间」排序返回，
高赞短评被系统性过度代表。因此：

- 均分、占比等指标只能描述「**可见样本**」，不能外推为该书读者总体；
- 时间趋势只能说明「**可见话语的漂移**」，不等同于真实评价史；
- 若要做严格的接受史/评价分布研究，必须换数据源（全量 API、商业数据库、平台合作），
  或明确把结论限定在「高赞可见话语」层面。

## 合规与礼貌抓取

- 豆瓣 www 域 `robots.txt` 声明 `Crawl-delay: 5`；book 子域无 robots.txt。
  脚本默认 **4–7 秒随机间隔 + 403 指数退避**，不要用 `--delay` 调低。
- 禁止并发、禁止绕过验证码、禁止大规模分发原始数据。
- 仅用于个人研究/教学的小规模采集；数据版权归平台与用户，引用注明来源。

## Cookie（可选，用于提高深度）

浏览器登录豆瓣 → F12 → Network → 任选一个 book.douban.com 请求 →
Request Headers → 复制整行 `Cookie` → 存成 `cookie.txt` → 用 `--cookie-file cookie.txt`。
**不要把 Cookie 写进命令行历史或提交到仓库。**

## 参数说明

`douban_fetch.py`

| 参数 | 说明 |
|---|---|
| `--query` | 只按书名检索候选题条目，不抓取 |
| `--id` | subject ID |
| `--status` | `P`=读过（默认）/ `F`=想读 / `N`=在读 |
| `--sort` | `hot`=热门 / `time`=最新 / `both`=合并去重（默认，覆盖更广） |
| `--max-pages` | 每种排序最多翻页数，默认 50 |
| `--delay` | 间隔秒数范围，默认 `4-7` |
| `--cookie-file` / `--cookie` | 登录态 |
| `--keep-html` | 保留原始 HTML 备查（建议用于留档核验） |

**断点续传**：数据按 `cid` 去重后增量写入 JSONL，中断后重跑同一命令即可续采。

## 分析维度

`douban_analyze.py` 产出（全部落在输出目录）：

| 文件 | 内容 |
|---|---|
| `stats.json` | 样本量、均分、标准差、极化度（归一化熵）、相关系数、覆盖率、方法论声明 |
| `rating_distribution.csv` | 1–5★ 分布 + 无评分 |
| `yearly_trend.csv` | 逐年评论数、均分、平均字数、平均有用数 |
| `length_distribution.csv` | 短评长度分桶 |
| `keywords_top.csv` | 高频关键词（TF-IDF 加权） |
| `keywords_by_rating.csv` | 高分(4–5★) vs 低分(1–2★) 特征词对比 |
| `yearly_keywords.csv` | 分时段关键词 —— 接受史漂移视角 |
| `top_comments.csv` | 高赞短评 Top 30 |

几个值得留意的导出指标：

- **极化度（归一化熵）**：接近 1 = 评价高度分化，接近 0 = 高度一致。
- **字数 × 评分 相关 r**：正值说明打分低的人反而写得更多（常见于争议性文本）。
- **高分/低分特征词对比**：直接呈现评价分歧的语义焦点。

### 依赖与降级

采集层**零第三方依赖**（纯标准库），一定能跑。分析层会自动降级：

| 缺失 | 降级方案 |
|---|---|
| `jieba` | 改用字符 n-gram + PMI 凝聚度做新词发现 |
| `pandas` / `numpy` | 纯 Python 统计 |
| `scikit-learn` | 手写 TF-IDF（本来就手写） |

装上 `jieba` 分词质量明显更好，建议装：
`pip install jieba`（或装到托管 venv）。

### 情感分析（谨慎使用）

默认 `--sentiment off`，**以豆瓣星级作为评价倾向的可靠代理**。

- `lexicon`：内置褒贬词典启发式；
- `snownlp`：调用 SnowNLP，需 `pip install snownlp`。

无论哪种，情感结果都属于**启发式辅助指标**，必须与星级做交叉验证，
**不得单独作为结论**，报告里也会印这句提示。

## 输出

`douban_report.py` 生成单文件 HTML（ECharts CDN）：总体指标卡片、评分分布、
年度趋势双轴图、关键词条形图、高低分特征词对比、长度分布、分时段关键词表、
高赞短评 Top 10、逐年明细表，以及顶部的**方法论与局限声明**。
离线环境下图表不渲染，但所有数据仍以表格完整呈现。

## 目录约定

```
douban_book_comments/
├── scripts/
│   ├── douban_fetch.py      采集（零依赖）
│   ├── douban_analyze.py    量化分析（可降级）
│   └── douban_report.py     HTML 报告
├── references/
│   └── analysis_dimensions.md   可拓展的分析维度与学术用法
└── data/                    运行产出：jsonl / csv / stats.json / report.html
```

## 排错

| 现象 | 原因与处理 |
|---|---|
| `start=180 code=403` | 未登录深度上限，正常停止；加 Cookie 或接受该样本量 |
| 连续 `403`/`无数据` | 触发风控，脚本自动退避；等 10–30 分钟再跑，调大 `--delay` |
| 解析出 0 条 | 页面结构可能变更，用 `--keep-html` 存 HTML 后检查 `comment-item` 结构 |
| 报告图表空白 | 需联网加载 ECharts；表格仍有完整数据 |
