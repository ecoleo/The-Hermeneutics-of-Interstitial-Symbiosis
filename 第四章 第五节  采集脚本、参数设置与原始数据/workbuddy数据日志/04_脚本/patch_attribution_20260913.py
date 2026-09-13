# -*- coding: utf-8 -*-
"""
词典归属更正补丁（2026-09-13，用户"执行"指令确认的三处修正之一、之二）。

修正一（方法段/选用理由段）：
  "类别测量采用分析前冻结的预登记词典（防止事后挑选词表迎合结论）"
  → 补入词典归属：词表由智能体在研究者设定的类目框架下起草、经研究者审定后冻结
  （AI-drafted, researcher-ratified，非研究者自编 self-constructed）。

修正二（交叉验证说明 B站句）：
  在 "z=−8.32）；" 后插入限定——两智能体共用同一预登记词表与采样协议，
  一致性验证的是采集与统计过程的真实性与可复现性，而非测量的独立性。

修正三（md 同步）：方法论说明与交叉验证说明.md 两处对应表述同步。

校验：每处旧串在目标文件中须唯一命中；替换后回读验证新串在位、旧串消失。
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from docx import Document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(ROOT, "交付_2026-09-12", "01_论文修订稿",
                    "第五节 接受-批判进路：《故事新编》数字传播生态的算法规训批判（修订稿）.docx")
MD = os.path.join(ROOT, "交付_2026-09-12", "05_复现说明",
                  "方法论说明与交叉验证说明.md")

OLD1 = "类别测量采用分析前冻结的预登记词典（防止事后挑选词表迎合结论）"
NEW1 = ("类别测量采用分析前冻结的预登记词典——词表由智能体在研究者设定的类目框架下"
        "起草、经研究者审定后冻结，以防止事后挑选词表迎合结论")

OLD2 = "z=−8.32）；豆瓣数据口径收敛"
ADD2 = ("须说明，两智能体共用同一预登记词表与采样协议，此处一致性验证的是采集与统计"
        "过程的真实性与可复现性，而非测量的独立性；")
NEW2 = "z=−8.32）；" + ADD2 + "豆瓣数据口径收敛"

# md 中的对应串（数字两侧带空格）
OLD2_MD = "z=−8.32）；豆瓣数据口径收敛"
NEW2_MD = "z=−8.32）；" + ADD2 + "豆瓣数据口径收敛"


def replace_in_paragraph(p, old, new):
    """runs 合并 → 首 run 写入 → 其余清空（沿用 revise_docx.py 模式）。"""
    full = "".join(r.text for r in p.runs)
    if old not in full:
        return False
    p.runs[0].text = full.replace(old, new)
    for r in p.runs[1:]:
        r.text = ""
    return True


def main():
    # ---------- docx ----------
    doc = Document(DOCX)
    for label, old, new in [("修正一", OLD1, NEW1), ("修正二", OLD2, NEW2)]:
        hits = [p for p in doc.paragraphs if old in p.text]
        assert len(hits) == 1, f"{label} 旧串命中数异常: {len(hits)}（预期 1）"
        assert replace_in_paragraph(hits[0], old, new), f"{label} 替换失败"
        print(f"[docx] {label} 完成（唯一命中）")
    doc.save(DOCX)

    # 回读验证
    doc2 = Document(DOCX)
    txt = "\n".join(p.text for p in doc2.paragraphs)
    assert NEW1 in txt and OLD1 not in txt, "修正一回读失败"
    assert NEW2 in txt and txt.count(ADD2) == 1, "修正二回读失败"
    print("[docx] 回读验证通过：新串在位、旧串消失")

    # ---------- md ----------
    with open(MD, encoding="utf-8") as f:
        md = f.read()
    assert md.count(OLD1) == 1, f"md 修正一命中数异常: {md.count(OLD1)}"
    assert md.count(OLD2_MD) == 1, f"md 修正二命中数异常: {md.count(OLD2_MD)}"
    md = md.replace(OLD1, NEW1).replace(OLD2_MD, NEW2_MD)
    with open(MD, "w", encoding="utf-8") as f:
        f.write(md)
    with open(MD, encoding="utf-8") as f:
        chk = f.read()
    assert NEW1 in chk and OLD1 not in chk and chk.count(ADD2) == 1, "md 回读失败"
    print("[md] 修正三（同步）完成，回读验证通过")

    print("\n全部三处修正落盘：", DOCX)
    print("               ", MD)


if __name__ == "__main__":
    main()
