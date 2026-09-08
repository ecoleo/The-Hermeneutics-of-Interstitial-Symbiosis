# -*- coding: utf-8 -*-
"""
BERTScore 计算：38 篇 AI 生成文本 vs 鲁迅《故事新编》八篇原作（多参照取最优）
以及 vs 人类批评者《造字》样章。
模型：bert-base-chinese（本地），取最后一层（第12层）隐状态，未缩放原始余弦 BERTScore。
"""
import json, re, csv, os, time
import torch
from transformers import BertTokenizerFast, BertModel

torch.set_num_threads(max(1, os.cpu_count() or 1))
MODEL = "models/bert-base-chinese"
tok = BertTokenizerFast.from_pretrained(MODEL)
model = BertModel.from_pretrained(MODEL, output_hidden_states=True)
model.eval()

STORIES = ['补天','奔月','理水','采薇','铸剑','出关','非攻','起死']
GROUPS = ['弱约束','中约束','强约束','参照组']
MODELS = ["通义千问","文心一言","DeepSeek","Kimi","智谱清言","豆包","腾讯元宝","讯飞星火","MiniMax","阶跃星辰"]
FAILED = {('强约束','阶跃星辰'), ('参照组','阶跃星辰')}  # 敏感词拦截，未生成

def clean_cand(t):
    out = []
    for ln in t.splitlines():
        s = ln.strip()
        if not s: continue
        if s.startswith('【') and s.endswith('】'): continue
        if re.fullmatch(r'[-—=*#\s]+', s): continue
        if s.startswith('#'): s = s.lstrip('#').strip()
        if re.match(r'^[《〈].*续篇?[》〉].*接续', s): continue
        if s.startswith('《造字》续篇'): continue
        out.append(s)
    return '\n'.join(out)

@torch.no_grad()
def encode(text):
    ids_full = tok.encode(text, add_special_tokens=False)
    vecs = []
    CH = 500
    for i in range(0, len(ids_full), CH):
        chunk = ids_full[i:i+CH]
        inp = torch.tensor([tok.cls_token_id] + chunk + [tok.sep_token_id]).unsqueeze(0)
        out = model(input_ids=inp)
        h = out.last_hidden_state[0, 1:-1, :]  # 去 CLS/SEP
        vecs.append(h)
    if not vecs:
        return torch.zeros(0, 768)
    return torch.cat(vecs, 0)

import numpy as np
def pair_prf(cv, rv, block=512):
    """cv: [nc,d] candidate, rv: [nr,d] reference -> P,R,F1 (greedy cosine, numpy实现)"""
    cv = cv.numpy(); rv = rv.numpy()
    cv = cv / np.linalg.norm(cv, axis=1, keepdims=True)
    rv = rv / np.linalg.norm(rv, axis=1, keepdims=True)
    nc, nr = cv.shape[0], rv.shape[0]
    max_c = np.zeros(nc, dtype=np.float32)
    max_r = np.zeros(nr, dtype=np.float32)
    for i in range(0, nc, block):
        sim = cv[i:i+block] @ rv.T  # [b,nr]
        max_c[i:i+block] = sim.max(1)
        np.maximum(max_r, sim.max(0), out=max_r)
    P = float(max_c.mean()); R = float(max_r.mean())
    F = 2*P*R/(P+R) if P+R > 0 else 0.0
    return P, R, F

cands_raw = json.load(open('candidates.json', encoding='utf-8'))
refs = json.load(open('refs.json', encoding='utf-8'))

print('encoding references ...')
ref_vecs = {k: encode(v) for k, v in refs.items()}
for k, v in ref_vecs.items(): print(' ', k, v.shape)

print('encoding candidates ...')
cand_vecs = {}
for g in GROUPS:
    for m in MODELS:
        key = f'{g}|{m}'
        if (g, m) in FAILED: continue
        t = clean_cand(cands_raw[key])
        cand_vecs[key] = (encode(t), len(t))
print('n candidates:', len(cand_vecs))

# 人类样章 vs 八篇原作（人类基准）
yz = ref_vecs['样章']
human_rows = {}
for s in STORIES:
    human_rows[s] = pair_prf(yz, ref_vecs[s])

rows = []
t0 = time.time()
for gi, g in enumerate(GROUPS):
    for m in MODELS:
        key = f'{g}|{m}'
        if key not in cand_vecs: continue
        cv, L = cand_vecs[key]
        per_story = {}
        for s in STORIES:
            per_story[s] = pair_prf(cv, ref_vecs[s])
        # 多参照：各指标分别取最优（BERTScore 多参照约定）
        P_best = max(v[0] for v in per_story.values())
        R_best = max(v[1] for v in per_story.values())
        # F1 以最优 F1 故事为准（更稳健），同时记录
        f1s = {s: v[2] for s, v in per_story.items()}
        best_story = max(f1s, key=f1s.get)
        F_best = f1s[best_story]
        P_at_best, R_at_best, _ = per_story[best_story]
        # vs 样章
        Ps, Rs, Fs = pair_prf(cv, yz)
        row = {'组': g, '模型': m, '字数': L, '最佳匹配原作': best_story,
               'P_原作': round(P_at_best,4), 'R_原作': round(R_at_best,4), 'F1_原作': round(F_best,4),
               'P_样章': round(Ps,4), 'R_样章': round(Rs,4), 'F1_样章': round(Fs,4)}
        for s in STORIES: row[f'F1_{s}'] = round(per_story[s][2],4)
        rows.append(row)
        print(f'{g:4s} {m:6s} F1原作={F_best:.4f}({best_story}) F1样章={Fs:.4f}')

print('elapsed min:', round((time.time()-t0)/60,1))

# 人类样章基准
human_best = max(human_rows, key=lambda k: human_rows[k][2])
print('人类样章 vs 原作 best:', human_best, [round(x,4) for x in human_rows[human_best]])

with open('bertscore_full.csv','w',encoding='utf-8-sig',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# 组均值汇总
import statistics as st
summary = {}
for g in GROUPS:
    grp = [r for r in rows if r['组']==g]
    summary[g] = {k: round(st.mean(r[k] for r in grp),4) for k in ['P_原作','R_原作','F1_原作','P_样章','R_样章','F1_样章']}
    summary[g]['n'] = len(grp)
    summary[g]['F1_原作_SD'] = round(st.pstdev(r['F1_原作'] for r in grp),4)
    summary[g]['F1_样章_SD'] = round(st.pstdev(r['F1_样章'] for r in grp),4)
json.dump({'rows':rows,'summary':summary,
           'human_vs_stories':{k:[round(x,4) for x in v] for k,v in human_rows.items()}},
          open('bertscore_result.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
