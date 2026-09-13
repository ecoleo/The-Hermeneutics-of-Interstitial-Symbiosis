# -*- coding: utf-8 -*-
"""
交叉验证"独立"表述裁断补丁（2026-09-13，用户授权"根据真实情况裁断"）。

事实基础（四平台验证关系异质，无单一形容词可诚实概括）：
  B站    = 独立实现的逐值复现（代码实现独立，词表共用）——"独立实现"属实，保留
  豆瓣   = 口径收敛（采样框不同）——接近独立测量
  微信读书 = 超集包含关系（豆包数据为子集）——非独立
  抖音   = 单源无对端——无交叉验证可言

裁断：
  E1 首句"进行独立交叉验证"→"进行交叉验证"（删"独立"）。
     不用"互补"：紧随其后的从句已言"数据能力呈互补关系"，再用会混淆能力分工与验证逻辑；
     不用"异源"：对 B站/豆瓣成立，对微信读书（同平台、子集关系）为误述。
  E2 末句"关键结论经双智能体独立实现交叉验证"→按平台精确化。
     此句另有更深的失实：抖音单源数据从未满足"交叉验证"这一条件，
     原表述作为全称断言对抖音不成立，须明示其对端范围与单源局限。

校验：两处旧串在 docx 与 md 中各唯一命中；替换后回读验证。
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

OLD1 = "本研究引入豆包智能体进行独立交叉验证，两智能体的数据能力呈互补关系"
NEW1 = "本研究引入豆包智能体进行交叉验证，两智能体的数据能力呈互补关系"

OLD2 = "关键结论经双智能体独立实现交叉验证。"
NEW2 = ("关键结论凡有对端数据者均经双智能体交叉核验（B站为独立实现的逐值复现，"
        "豆瓣为口径收敛，微信读书为超集核对）；抖音为单源数据，未经交叉核验，"
        "其结论仅以前两重条件为限、止于可见性结构描述。")


def replace_in_paragraph(p, old, new):
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
    for label, old, new in [("E1 首句删「独立」", OLD1, NEW1),
                            ("E2 末句按平台精确化", OLD2, NEW2)]:
        hits = [p for p in doc.paragraphs if old in p.text]
        assert len(hits) == 1, f"{label} docx 命中数异常: {len(hits)}（预期 1）"
        assert replace_in_paragraph(hits[0], old, new), f"{label} docx 替换失败"
        print(f"[docx] {label} 完成（唯一命中）")
    doc.save(DOCX)

    doc2 = Document(DOCX)
    txt = "\n".join(p.text for p in doc2.paragraphs)
    assert NEW1 in txt and txt.count(OLD1) == 0, "E1 docx 回读失败"
    assert txt.count(NEW2) == 1 and txt.count(OLD2) == 0, "E2 docx 回读失败"
    # 段13 保留项核验：B站"独立实现"表述仍在且仅一处
    assert txt.count("独立实现的逐值复现") == 2, "B站『独立实现』保留项异常（预期2处：正文句+条件句）"
    print("[docx] 回读验证通过；B站『独立实现的逐值复现』按预期保留")

    # ---------- md ----------
    with open(MD, encoding="utf-8") as f:
        md = f.read()
    assert md.count(OLD1) == 1, f"E1 md 命中数异常: {md.count(OLD1)}"
    assert md.count(OLD2) == 1, f"E2 md 命中数异常: {md.count(OLD2)}"
    md = md.replace(OLD1, NEW1).replace(OLD2, NEW2)
    with open(MD, "w", encoding="utf-8") as f:
        f.write(md)
    with open(MD, encoding="utf-8") as f:
        chk = f.read()
    assert chk.count(NEW1) == 1 and chk.count(OLD1) == 0, "E1 md 回读失败"
    assert chk.count(NEW2) == 1 and chk.count(OLD2) == 0, "E2 md 回读失败"
    assert chk.count("独立实现的逐值复现") == 2, "md B站保留项异常"
    print("[md] 同步完成，回读验证通过")

    print("\n裁断补丁落盘：", DOCX)
    print("              ", MD)


if __name__ == "__main__":
    main()
