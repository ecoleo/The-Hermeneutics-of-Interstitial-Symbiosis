# -*- coding: utf-8 -*-
import csv, statistics as st, json
rows = list(csv.DictReader(open('bertscore_full.csv', encoding='utf-8-sig')))
groups = ['弱约束','中约束','强约束','参照组']
print('=== 组汇总（总体标准差 pstdev）===')
for g in groups:
    sub = [r for r in rows if r['组']==g]
    for ref in ['原作','样章']:
        P=[float(r['P_'+ref]) for r in sub]; R=[float(r['R_'+ref]) for r in sub]; F=[float(r['F1_'+ref]) for r in sub]
        print('%s 对%s n=%d P%.4f R%.4f F1=%.4f SD=%.4f  范围%.3f-%.3f' %
              (g,ref,len(sub),st.mean(P),st.mean(R),st.mean(F),st.pstdev(F),min(F),max(F)))
print()
refF=[float(r['F1_样章']) for r in rows if r['组']=='参照组']
print('参照组对样章: min=%.3f max=%.3f 全部>0.756? %s' % (min(refF),max(refF), all(x>0.756 for x in refF)))
origF=[float(r['F1_原作']) for r in rows]
print('对原作总范围 %.3f - %.3f' % (min(origF),max(origF)))
gm=[st.mean([float(r['F1_原作']) for r in rows if r['组']==g]) for g in groups]
print('对原作组均值极差 %.4f' % (max(gm)-min(gm)))
gm2=[st.mean([float(r['F1_样章']) for r in rows if r['组']==g]) for g in groups]
print('对样章组均值极差 %.4f' % (max(gm2)-min(gm2)))
j=json.load(open('bertscore_result.json',encoding='utf-8'))
print('human_vs_stories:', json.dumps(j.get('human_vs_stories',{}), ensure_ascii=False)[:400])
# 豆包逐组
print()
for r in rows:
    if r['模型']=='豆包': print('豆包', r['组'], '原作F%.3f 样章F%.3f'%(float(r['F1_原作']),float(r['F1_样章'])))
# 中约束两离群
for r in rows:
    if r['组']=='中约束' and r['模型'] in ('Kimi','阶跃星辰'):
        print('离群', r['模型'], '原作F%.3f 样章F%.3f'%(float(r['F1_原作']),float(r['F1_样章'])))
# 参照组最高单点
rr=[r for r in rows if r['组']=='参照组']
mx=max(rr,key=lambda r:float(r['F1_样章']))
print('参照组最高:',mx['模型'],mx['F1_样章'])
