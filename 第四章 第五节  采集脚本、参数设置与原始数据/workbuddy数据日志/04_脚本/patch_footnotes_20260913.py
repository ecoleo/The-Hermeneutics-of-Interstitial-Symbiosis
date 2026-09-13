# -*- coding: utf-8 -*-
"""
脚注体系修复 + 数字副文本概念界定插入（2026-09-13）。

问题一（修复）：此前 R1–R24 与各补丁采用"runs 合并→清空其余"替换法，把落在被替换
段落中的脚注引用 run（w:footnoteReference）一并清除——原始 docx 正文 53 处引用，
修订稿仅剩 35 处，18 处丢失（footnotes.xml 条目仍在，正文锚点没了）。
本脚本按原始 docx 的文本锚点逐一定位，外科式插回引用 run（不再整段重建）。

问题二（插入）：段11 首句后插入"数字副文本"概念界定（用户拟稿＋体例适配），
挂两条新脚注（id 55=Genette 法文原版+英译本双列；id 56=Birke & Christ 与
Desrochers & Apollon 合并），外文格式参照 Jockers 体例。原稿文内"（Genette，1987）"
按顺序编码脚注制转为脚注，不入正文。

插入的限定句已按实际论述校准（段11(三)"内容形态构成"与段25 开放编码类目）。

校验：18 处锚点唯一命中；插回后正文引用总数 55（35+18+2）；
引用 id 集合 = 原始引用集 ∪ {55,56}；段11 含界定文字；docx 可正常重开。
"""
import copy
import io
import os
import sys
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import lxml.etree as etree
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(ROOT, "交付_2026-09-12", "01_论文修订稿",
                    "第五节 接受-批判进路：《故事新编》数字传播生态的算法规训批判（修订稿）.docx")
ORIG = os.path.join(ROOT, "第五节 接受-批判进路：《故事新编》数字传播生态的算法规训批判.docx")
MD = os.path.join(ROOT, "交付_2026-09-12", "05_复现说明", "方法论说明与交叉验证说明.md")

FN55 = ("Genette,Gérard.Seuils[M].Paris:Éditions du Seuil,1987；英译本："
        "Genette,Gérard.Paratexts:Thresholds of Interpretation[M]."
        "Lewin J E,trans.Cambridge:Cambridge University Press,1997.")
FN56 = ("Birke,Dorothee,Christ,Birte.Paratext and Digitized Narrative:Mapping the "
        "Field[J].Narrative,2013,21(1):65-87；Desrochers,Danielle,Apollon,Daniel."
        "Examining Paratextual Theory and its Applications in Digital Culture[M]."
        "Hershey:IGI Global,2014.")

PART_A = ("这里所称“数字副文本”，沿用热奈特“副文本是环绕正文并引导读者进入文本的"
          "门槛装置”的界定")
PART_B = ("，并延伸到数字环境：印刷时代由作者与出版者主导的书名、序言、注释、评论等，"
          "在数字平台演变为由平台算法与用户共同生产的标签、分类、话题、短评、划线与人气排序")
PART_C = ("。需要说明的是，“数字副文本”在此指研究对象而非某种既定分析程式，本节实际"
          "采用的分析方法是内容分析与描述统计（预登记词典、开放编码、频次与占比、比例检验），"
          "以保证每一条归类可人工复核、全部统计可复现。其中抖音短视频本体属衍生创作文本"
          "而非副文本，本节仅将其话题与检索入口作为副文本层面的可见性材料，其内容形态构成"
          "则按开放编码程序单独处理，不与副文本归类混同。")


# ---------- 工具函数 ----------

def para_runs(p):
    """段落的 run 列表（按文档顺序，含零文本的引用 run）。"""
    return list(p.iter(qn("w:r")))


def run_text(r):
    return "".join(t.text or "" for t in r.findall(qn("w:t")))


def para_text(p):
    """段落纯文本：w:t 拼接，脚注引用占零宽。"""
    return "".join(run_text(r) for r in para_runs(p))


def new_text_run(rpr_src, text):
    r = OxmlElement("w:r")
    if rpr_src is not None:
        r.append(copy.deepcopy(rpr_src))
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def new_ref_run(rpr_src, fid):
    r = OxmlElement("w:r")
    rpr = copy.deepcopy(rpr_src) if rpr_src is not None else OxmlElement("w:rPr")
    for va in rpr.findall(qn("w:vertAlign")):
        rpr.remove(va)
    va = OxmlElement("w:vertAlign")
    va.set(qn("w:val"), "superscript")
    rpr.append(va)
    r.append(rpr)
    ref = OxmlElement("w:footnoteReference")
    ref.set(qn("w:customMarkFollows"), "0")
    ref.set(qn("w:id"), str(fid))
    r.append(ref)
    return r


def insert_elements_at(p, offset, elements):
    """在段落文本 offset 处（零宽引用口径）依序插入 elements。"""
    acc = 0
    for r in para_runs(p):
        if r.find(qn("w:footnoteReference")) is not None:
            continue  # 引用 run 零宽
        rt = run_text(r)
        if acc + len(rt) < offset:
            acc += len(rt)
            continue
        k = offset - acc  # 0 <= k <= len(rt)
        rpr = r.find(qn("w:rPr"))
        if k == 0:
            for el in elements:
                r.addprevious(el)
            return
        if k == len(rt):
            prev = r
            for el in elements:
                prev.addnext(el)
                prev = el
            return
        # 需要拆分 run（要求单 w:t）
        assert len(r.findall(qn("w:t"))) == 1, "目标 run 含多个 w:t，需人工处理"
        t = r.find(qn("w:t"))
        r2 = copy.deepcopy(r)
        t.text = rt[:k]
        r2.find(qn("w:t")).text = rt[k:]
        r.addnext(r2)
        prev = r
        for el in elements:
            prev.addnext(el)
            prev = el
        return
    raise RuntimeError(f"offset {offset} 超出段落文本长度")


def zip_refs(path):
    """读取 docx 包：{ref_id: (before_ctx, after_ctx)} 与引用 id 集。"""
    z = zipfile.ZipFile(path)
    doc = z.read("word/document.xml").decode("utf-8")
    import re
    paras = re.findall(r"<w:p [^>]*>.*?</w:p>|<w:p/>", doc, re.S)
    out = {}
    for pxml in paras:
        txt, refs = "", []
        for m in re.finditer(
                r'<w:footnoteReference[^>]*?w:id="(\d+)"|<w:t[^>]*>([^<]*)</w:t>', pxml):
            if m.group(1) is not None:
                refs.append((len(txt), int(m.group(1))))
            else:
                txt += m.group(2)
        for pos, rid in refs:
            out[rid] = (txt[max(0, pos - 18):pos], txt[pos:pos + 18])
    return out, set(out)


def main():
    orig_map, orig_ids = zip_refs(ORIG)
    rev_map, rev_ids = zip_refs(DOCX)
    missing = sorted(orig_ids - rev_ids)
    assert len(missing) == 18, f"丢失引用数异常: {len(missing)}"
    print(f"[诊断] 丢失引用 {len(missing)} 处: {missing}")

    doc = Document(DOCX)
    body = doc.element.body
    paras = list(body.iter(qn("w:p")))
    texts = [para_text(p) for p in paras]

    # ---------- 1. 修复 18 处丢失引用 ----------
    # 锚定策略：引用标记挂在引文句末，故统一以"前文末段"为锚（18 处引文本体均存留，
    # 其中 4 处后续句被改写，不影响标记位置）
    print("\n== 修复丢失引用（锚点唯一命中校验）==")
    restored = 0
    for rid in missing:
        before, after = orig_map[rid]
        frag = before[-12:]
        hits = [(pi, texts[pi].find(frag)) for pi in range(len(texts))
                if frag in texts[pi]]
        assert len(hits) == 1 and hits[0][1] >= 0, \
            f"id={rid} 引文锚点命中数异常: {hits}（frag={frag!r}）"
        pi, idx = hits[0]
        offset = idx + len(frag)
        p = paras[pi]
        rpr_src = None
        for r in para_runs(p):
            if run_text(r):
                rpr_src = r.find(qn("w:rPr"))
                break
        insert_elements_at(p, offset, [new_ref_run(rpr_src, rid)])
        restored += 1
        print(f"  id={rid} -> 段{pi} 位{offset} …{frag}◆")
    assert restored == 18

    # ---------- 2. 段11 插入概念界定 + 两条新脚注引用 ----------
    print("\n== 插入数字副文本概念界定（段11 首句后）==")
    tgt = None
    for p in paras:
        if "本部分运用数字副文本分析方法" in para_text(p):
            tgt = p
            break
    assert tgt is not None, "未找到段11"
    t11 = para_text(tgt)
    anchor = "相关内容的可观测材料。"
    assert t11.count(anchor) == 1, "段11 首句锚点异常"
    offset = t11.find(anchor) + len(anchor)
    rpr_src = None
    for r in para_runs(tgt):
        if run_text(r):
            rpr_src = r.find(qn("w:rPr"))
            break
    elements = [
        new_text_run(rpr_src, PART_A), new_ref_run(rpr_src, 55),
        new_text_run(rpr_src, PART_B), new_ref_run(rpr_src, 56),
        new_text_run(rpr_src, PART_C),
    ]
    insert_elements_at(tgt, offset, elements)
    print("  段11 界定文字 + 引用55/56 已插入")

    # ---------- 3. footnotes.xml 追加两条新脚注 ----------
    print("\n== 追加脚注条目 55/56 ==")
    fp = None
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/footnotes"):
            fp = rel.target_part
    assert fp is not None, "未找到 footnotes 部件"
    froot = etree.fromstring(fp.blob)
    template = None
    for fn in froot:
        if fn.tag == qn("w:footnote") and fn.get(qn("w:id")) == "9":
            template = fn
            break
    assert template is not None
    # 模板正文 run 的 rPr（引用文本格式）——run 位于 w:p 内
    text_rpr = None
    tpl_p = template.find(qn("w:p"))
    for r in tpl_p.findall(qn("w:r")):
        if run_text(r).strip():
            text_rpr = r.find(qn("w:rPr"))
            break
    existing_ids = {fn.get(qn("w:id")) for fn in froot if fn.tag == qn("w:footnote")}
    for fid, text in [(55, FN55), (56, FN56)]:
        assert str(fid) not in existing_ids
        clone = copy.deepcopy(template)
        clone.set(qn("w:id"), str(fid))
        c_p = clone.find(qn("w:p"))
        keep_ref_run = False
        for r in c_p.findall(qn("w:r")):
            if r.find(qn("w:footnoteRef")) is not None:
                keep_ref_run = True
                continue
            c_p.remove(r)
        assert keep_ref_run
        c_p.append(new_text_run(text_rpr, " " + text))
        froot.append(clone)
        print(f"  脚注 id={fid} 已追加（{len(text)} 字）")
    fp._blob = etree.tostring(froot, xml_declaration=True,
                              encoding="UTF-8", standalone=True)

    doc.save(DOCX)
    print("\n已保存:", DOCX)

    # ---------- 4. 回读验证 ----------
    print("\n== 回读验证 ==")
    z = zipfile.ZipFile(DOCX)
    dxml = z.read("word/document.xml").decode("utf-8")
    import re
    ref_ids = [int(x) for x in re.findall(r'<w:footnoteReference[^>]*?w:id="(\d+)"', dxml)]
    print(f"  正文引用总数: {len(ref_ids)}（预期 55 = 35+18+2）")
    assert len(ref_ids) == 55
    assert set(ref_ids) == orig_ids | {55, 56}, "引用 id 集合与预期不符"
    assert len(ref_ids) == len(set(ref_ids)), "存在重复引用 id"
    fxml = z.read("word/footnotes.xml").decode("utf-8")
    for fid in (55, 56):
        m = re.search(r'<w:footnote [^>]*w:id="%d".*?</w:footnote>' % fid, fxml, re.S)
        assert m, f"脚注 {fid} 未写入"
        ftxt = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(0)))
        print(f"  脚注 {fid} 文本: {ftxt[:70]}…")
    doc2 = Document(DOCX)
    t11b = None
    for p in doc2.paragraphs:
        if "本部分运用数字副文本分析方法" in p.text:
            t11b = p.text
            break
    assert t11b and "这里所称“数字副文本”" in t11b and "门槛装置”的界定" in t11b \
        and "不与副文本归类混同" in t11b
    i = t11b.find("这里所称")
    print("  段11 界定段（前120字）:", t11b[i:i + 120])
    print("\n全部验证通过。请在 Word/WPS 中打开确认脚注编号显示正常（应自动顺延）。")


if __name__ == "__main__":
    main()
