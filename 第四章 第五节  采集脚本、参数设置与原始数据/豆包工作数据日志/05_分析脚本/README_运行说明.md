# 分析脚本与运行说明（05_分析脚本）

本目录为论文第五节数字副文本**采集 → 解析 → 统计 → 出图 → 论文修订**全流程脚本。全部为 Python，采集脚本仅用标准库，分析脚本依赖 pandas/numpy/matplotlib/jieba/python-docx。

## 0. 环境与依赖
- Python 3.14.7（3.10+ 应均可）；Windows + PowerShell（`;` 分隔命令）。
```
pip install pandas==3.0.5 numpy==2.5.2 matplotlib==3.11.1 jieba==0.42.1 python-docx==1.2.0
```
- 脚本内 `BASE` 为研究项目根目录的**绝对路径**，换机器复现时请统一修改各脚本顶部的 `BASE`。
- 所有凭据（Cookie / API Key）一律经**环境变量**传入，脚本不硬编码、不写入结果文件。

## 1. 脚本清单与执行顺序

| 顺序 | 脚本 | 阶段 | 输入 | 输出 | 凭据/说明 |
|---|---|---|---|---|---|
| 1a | `bili_fetch.py` | B站采集 | B站公开搜索接口 | `data/bili/bili_*.jsonl`、`*_meta.json` | 无需登录；自实现 WBI 签名；3 关键词×2 排序×8 页，请求间隔约 1.5s |
| 1b | `douban_fetch.py` | 豆瓣采集 | subject 2046909 短评页 | `data/douban_2046909_auth/comments_2046909_P.jsonl` | 需 `$env:DOUBAN_COOKIE`；热门/最新各 5 页，间隔默认 18s（`DOUBAN_SLEEP` 可调）；匿名态 time 排序会 403 |
| 1c | `weread_fetch_v2.py` | 微信读书采集 | 官方 Agent API | `data/weread_故事新编_采集_<日期>.json` | 需 `$env:WEREAD_API_KEY`；skill_version=1.0.4，参数平铺；返回结果已递归匿名 |
| 1d | 抖音（浏览器人工辅助，**无独立脚本**） | 抖音采集 | 抖音网页版搜索 | `data/douyin/douyin_*_raw.jsonl` | 见下方第 3 节，需两次人工接管 |
| 2 | `douyin_parse.py` | 抖音解析编码 | 1d 的 raw.jsonl | `data/douyin/douyin_parsed.csv` | 点赞"万/亿"换算、时长转秒、按锁定编码本归类 |
| 3 | `bili_analyze.py` | B站统计 | 1a 的 jsonl | `data/bili/bili_category_stats.csv`、`bili_order_tests.csv`、`bili_tags_top.csv` | 预登记四类词典、Wilson 95%CI、两比例 z 检验。命令行参数 `--data-dir`、`--out` |
| 4 | `analysis_all.py` | 统一出图 | 上述全部 | `data/analysis/*.csv` + `04_分析图表/图1—图6.png` | 300 dpi、SimHei、嵌入宽 5.8 英寸 |
| 5 | `summary_stats.py` | 汇总统计量 | 上述全部 | `data/analysis/summary_stats.json`（论文数字唯一权威源），并打印关键数字 | 由原始数据现算 |
| 6a | `revision_texts.py` | 论文新文本 | — | 供 6b 导入（13 段新文本 + 6 图映射） | 改措辞改此文件 |
| 6b | `apply_revision2.py` | 生成修订稿 | 原稿 docx 副本 + 图 | `03_论文修订稿/…（数字副文本实证修订稿）.docx` | 继承原字体，整段替换+插图 |
| 6c | `refine_theory.py` | 理论段边界限定 | 6b 产物 | 原地更新 | 给"扁平化"段加经验边界 |
| 6d | `patch_douban_wording.py` | 豆瓣措辞精确化（历史补丁） | 旧版稿 | 原地更新 | **当前 `revision_texts.py` 已内置精确表述，从干净原稿重建（6a→6b→6c）时无需运行 6d**；该脚本仅用于把更早的"词频均为0"旧稿就地修正 |
| 附 | `collect_data.py` | 交付数据归集+脱敏 | data/ 全部 | `02_平台采集数据/` | 昵称/UID 匿名、移除 mid、@昵称替换 |

> 论文修订脚本（6a—6d）依赖 `python-docx`；如只复现数据分析与图表，跑到第 5 步即可。

## 2. 一键复现数据分析（采集已完成时）
在项目根目录依次：
```powershell
python scripts/douyin_parse.py
python scripts/bili_analyze.py --data-dir data/bili --out data/bili
python scripts/analysis_all.py
python scripts/summary_stats.py
```
预期：`data/analysis/summary_stats.json` 与交付版一致；`04_分析图表/` 重新生成 6 张 PNG，数值与论文一致。

## 3. 抖音采集的浏览器人工辅助步骤（对应论文"两次人工接管"）
requests 直连因缺 `a_bogus` 签名不可行（返回空 data/验证码页），改用平台内置受控浏览器（Browser Use，`computer_use_tool, plane="bu"`，库 `seed_browser_use`）：
1. `bu.navigate` 打开 `https://www.douyin.com/search/鲁迅说?type=general`；
2. 出现登录弹窗 → `interaction.request_action(type="browserControl")` 请研究者**扫码登录**，交还后 `bu.snapshot()` 确认；
3. 循环 14 轮：`bu.js("window.scrollBy(0,1500)")` → sleep 2.0s → 读取 `div.search-result-card` 的 innerText，按内容去重，直到计数不再增长，得 147 条，写入 raw.jsonl；
4. 改检索词 `故事新编 鲁迅`（URL 编码 `%E6%95%85%E4%BA%8B%E6%96%B0%E7%BC%96%20%E9%B2%81%E8%BF%85`），遇图形拖拽验证码 → 再次 `request_action` 请研究者**手动通过**，重采得 18 条；
5. 过滤以"相关搜索"开头的推荐卡；raw 行格式 `{query, raw}`，交给步骤 2 的 `douyin_parse.py`。
> 该路径无法脱离受控浏览器与人工接管完全无人值守运行，这是平台反自动化机制决定的，已在论文与复现说明中如实声明。

## 4. 编码本与统计口径（速查）
- B站四类标签词典、抖音六类编码本与优先级、微信读书 chapterUid→篇目映射，分别在 `bili_analyze.py`、`douyin_parse.py`、`analysis_all.py` 文件开头常量区，均为**分析前锁定**版本。
- 抖音"碎片化"＝名句呈现+仿写玩梗+共鸣纪念；"深度"＝知识讲解+剧情演绎。
- 图6 只并列同口径三组（抖音×2、微信读书），B站标签口径与豆瓣短评口径不混入该图。
- 检验为描述性：综合/最新样本有重叠、非独立、未做多重比较校正，论文不作因果断言。

## 5. 输出与交付对应
- 图表 → `04_分析图表/`（6 张，300 dpi）；
- 脱敏数据 → `02_平台采集数据/`（运行 `collect_data.py` 重新生成）；
- 论文修订稿 → `03_论文修订稿/`；
- 数字核对源 → `02_平台采集数据/汇总统计/summary_stats.json`，逐条对照见 `01_复现说明/复现说明.md` 第六节核对表。
