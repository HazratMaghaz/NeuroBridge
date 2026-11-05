#!/usr/bin/env python3
"""Development-only Phase 9A/9B/9C-like gene/program selection and Phase 11A Ridge.

Pathway choices are recomputed on development only, using a PREDEFINED GMT library
or optional live Enrichr. Previously outcome-selected Phase9C results are never inputs.
"""
from __future__ import annotations
import argparse, hashlib, re
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import hypergeom
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression,RidgeCV
from sklearn.pipeline import make_pipeline
from nbv3_common import load_dataset, ensure_fresh_output, filehash, write_json, ANNO


def bh(p):
    p=np.nan_to_num(np.asarray(p,dtype=float),nan=1.0,posinf=1.0,neginf=1.0)
    idx=np.argsort(p);n=len(p)
    out=np.empty(n); out[idx]=np.clip(np.minimum.accumulate((p[idx]*n/np.arange(1,n+1))[::-1])[::-1],0,1)
    return out

def safe_corr(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if len(a)<3 or np.std(a)<1e-10 or np.std(b)<1e-10:return np.nan
    return float(np.corrcoef(a,b)[0,1])

def get_annotation(path,genes):
    if not Path(path).is_file():raise FileNotFoundError(path)
    a=pd.read_csv(path)
    gid='gene_id_clean' if 'gene_id_clean' in a else ('gene_id' if 'gene_id' in a else None)
    sym='gene_name' if 'gene_name' in a else ('gene_symbol_matrix' if 'gene_symbol_matrix' in a else None)
    if not gid or not sym:raise ValueError(f'Annotation missing expected IDs/symbols: {a.columns.tolist()[:20]}')
    a['clean_id']=a[gid].astype(str).str.extract(r'(ENSG\d+)',expand=False)
    a['symbol']=a[sym].astype(str).str.strip()
    if 'gene_type' in a:
        a=a[a['gene_type'].astype(str).eq('protein_coding')]
    elif 'gene_biotype' in a:
        a=a[a['gene_biotype'].astype(str).eq('protein_coding')]
    else:raise ValueError('Annotation must identify protein_coding genes via gene_type or gene_biotype')
    a=a.dropna(subset=['clean_id']).drop_duplicates('clean_id')
    am=dict(zip(a.clean_id,a.symbol)); gm={g:am.get(re.search(r'ENSG\d+',g).group(0),'') for g in genes}
    return gm

def load_gmt(path):
    sets={}
    if path:
        with open(path) as f:
            for line in f:
                s=line.rstrip('\n').split('\t')
                if len(s)>=5:sets[s[0]]=list(dict.fromkeys([x.strip() for x in s[2:] if x.strip()]))
    return sets

def enriched_pathways_from_gmt(sets,program_lists,available_syms,max_terms=20):
    # All quantities derived using only development-selected lists and a fixed external gene library.
    universe=set(available_syms);res=[]
    for source,sg in program_lists.items():
        query=set(sg)&universe
        for name,genes in sets.items():
            gs=set(genes)&universe; overlap=query&gs
            if len(gs)<5 or len(overlap)<3 or len(query)==0:continue
            p=hypergeom.sf(len(overlap)-1,len(universe),len(gs),len(query))
            res.append(dict(source=source,term=name,p_value=p,overlap_size=len(overlap),
                            gene_symbols=';'.join(sorted(overlap)),term_gene_count=len(gs)))
    if not res:return pd.DataFrame(),{}
    df=pd.DataFrame(res);df['adjusted_p_value']=np.nan
    for source,inds in df.groupby('source').groups.items(): df.loc[inds,'adjusted_p_value']=bh(df.loc[inds,'p_value'])
    df=df.sort_values(['adjusted_p_value','p_value','term'],kind='stable').reset_index(drop=True)
    chosen=df[df.adjusted_p_value<=.05].head(max_terms).copy()
    defs={f"pathway__{row.source}__{re.sub('[^A-Za-z0-9]+','_',row.term)[:52]}":row.gene_symbols.split(';')
          for row in chosen.itertuples()}
    return df,defs

def enriched_pathways_from_enrichr(program_lists,max_terms=20):
    """Optional live reproduction of Phase9C Enrichr approach with NEW development-only lists.
    This sends gene SYMBOL lists (no patient IDs or expression values) to Enrichr.
    Saved results must be inspected before reporting; library contents can change.
    """
    try:import gseapy as gp
    except ImportError as e:raise ImportError('For --enrichr install gseapy in your conda environment') from e
    desired=['MSigDB_Hallmark_2020','GO_Biological_Process_2023','KEGG_2021_Human','Reactome_2022']
    try:available=gp.get_library_name(organism='human')
    except Exception:available=gp.get_library_name(organism='Human')
    selected=[x for x in desired if x in available]
    for old,new in [('GO_Biological_Process_2023','GO_Biological_Process_2025'),
                    ('Reactome_2022','Reactome_Pathways_2024'),('KEGG_2021_Human','KEGG_2019_Human')]:
        if old not in selected and new in available:selected.append(new)
    if not selected:raise RuntimeError('No matching Enrichr gene-set libraries available')
    results=[]
    for name,genes in program_lists.items():
        if len(genes)<5:continue
        for lib in selected:
            enr=gp.enrichr(gene_list=genes,gene_sets=lib,organism='human',outdir=None,cutoff=1.,verbose=False)
            df=enr.results.copy()
            if df.empty:continue
            df['gene_list_name']=name;df['gene_set_library']=lib
            results.append(df)
    if not results:raise RuntimeError('Enrichr returned no results; no silent fallback to historical lists')
    all_res=pd.concat(results,ignore_index=True)
    adj=next((c for c in all_res.columns if 'adjusted' in c.lower()),None)
    if 'Term' not in all_res or 'Genes' not in all_res or adj is None:
        raise ValueError(f'Unexpected Enrichr output columns: {all_res.columns.tolist()}')
    all_res['adjusted_p_value_used']=pd.to_numeric(all_res[adj],errors='coerce')
    all_res=all_res.sort_values(['adjusted_p_value_used','Term'],kind='stable')
    top=all_res[all_res.adjusted_p_value_used<=.05].head(max_terms)
    defs={}
    for row in top.itertuples():
        key=f"pathway__{row.gene_list_name}__{re.sub('[^A-Za-z0-9]+','_',row.Term)[:45]}"
        genes=[g.strip() for g in re.split(r'[;,]',str(row.Genes)) if g.strip()]
        if len(genes)>=3:defs[key]=genes
    return all_res,defs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',default='.');ap.add_argument('--run-id',required=True)
    ap.add_argument('--gmt',default=None,help='Predefined independent GMT database; optional; used for enriched pathway terms')
    ap.add_argument('--enrichr',action='store_true',help='Run development-only Enrichr selection on original Phase9C library types; needs gseapy and internet')
    ap.add_argument('--top-var-ml',type=int,default=5000);ap.add_argument('--top-genes-morph',type=int,default=5000)
    ap.add_argument('--max-pathways',type=int,default=20);ap.add_argument('--demo',action='store_true');args=ap.parse_args()
    if args.gmt and args.enrichr:raise ValueError('Choose --gmt or --enrichr, not both')
    root=Path(args.project);ref,E,I,genes,files=load_dataset(root,demo=args.demo)
    out=ensure_fresh_output(root/'results'/'corrected_v3'/args.run_id/'biology')
    anno=root/ANNO
    provenance={'status':'RUNNING','protocol':'Development-only target selection, fixed historical 103-patient test re-evaluation',
                'params':vars(args),'input_sha256':{**{k:filehash(v) for k,v in files.items()},'annotation':filehash(anno)}}
    if args.gmt:provenance['input_sha256']['gmt']=filehash(args.gmt)
    write_json(out/'manifest.json',provenance)
    dev=np.flatnonzero(ref.split.isin(['train','val']));te=np.flatnonzero(ref.split.eq('test'))
    if set(dev)&set(te):raise AssertionError('Canonical split overlaps')
    y=ref.y.to_numpy();EX=E[dev];GX=I[dev];ids=ref.patient_id.to_numpy()
    gm=get_annotation(anno,genes)
    eligible=np.array([i for i,g in enumerate(genes) if gm[g] not in ['', 'nan', 'None']])
    if len(eligible)<100:raise ValueError('Few mapped protein-coding gene columns, inspect annotation')
    # Training-development-only Phase 9A Welch DE, Cohen d and FDR.
    a=EX[:,eligible];ydev=y[dev];gb=a[ydev==1];lg=a[ydev==0]
    means_gb=gb.mean(0);means_lg=lg.mean(0);delta=means_gb-means_lg
    pooled=np.sqrt((gb.var(0,ddof=1)+lg.var(0,ddof=1))/2)
    d=delta/np.maximum(pooled,1e-8)
    p=stats.ttest_ind(gb,lg,axis=0,equal_var=False,nan_policy='omit').pvalue
    de=pd.DataFrame({'gene_id':[genes[i] for i in eligible], 'gene_symbol':[gm[genes[i]] for i in eligible],
       'logFC_GBM_minus_LGG':delta,'cohen_d':d,'abs_cohen_d':abs(d),'p_value':np.nan_to_num(p,nan=1),
       'fdr_bh':bh(p),'direction':np.where(delta>=0,'GBM_high','LGG_high')})
    de=de.sort_values(['fdr_bh','abs_cohen_d'],ascending=[True,False],kind='stable')
    de.to_csv(out/'phase9a_de_DEVELOPMENT_ONLY.csv',index=False)
    # Phase9A gene coefficient ranking: feature variance selection fitted on development only.
    var=a.var(0);top=np.argsort(-var,kind='stable')[:min(args.top_var_ml,len(eligible))]
    ml=make_pipeline(StandardScaler(),LogisticRegression(penalty='l1',solver='liblinear',class_weight='balanced',C=.1,max_iter=5000,random_state=42))
    ml.fit(a[:,top],ydev);coef=ml.named_steps['logisticregression'].coef_.reshape(-1)
    clf_rank=pd.DataFrame({'gene_id':[genes[eligible[j]] for j in top],'abs_ml_coefficient':np.abs(coef)})
    combined=de.merge(clf_rank,on='gene_id',how='left')
    combined['abs_ml_coefficient']=combined.abs_ml_coefficient.fillna(0)
    combined['score']=(1/combined.fdr_bh.rank(method='min')+1/combined.abs_cohen_d.rank(ascending=False,method='min')+
                       1/combined.abs_ml_coefficient.rank(ascending=False,method='min'))
    combined=combined.sort_values('score',ascending=False,kind='stable')
    combined.to_csv(out/'phase9a_candidate_biomarkers_DEVELOPMENT_ONLY.csv',index=False)
    # Morphology PCs constructed on development only and gene correlations on same rows.
    scaler=StandardScaler().fit(GX);pca=PCA(n_components=min(10,len(dev)-1,I.shape[1]),random_state=42)
    Z=pca.fit_transform(scaler.transform(GX))
    candidate=combined.head(min(args.top_genes_morph,len(combined))).copy()
    index={g:i for i,g in enumerate(genes)}
    XA=EX[:,[index[g] for g in candidate.gene_id]]
    XAs=(XA-XA.mean(0))/(XA.std(0)+1e-8);Zs=(Z-Z.mean(0))/(Z.std(0)+1e-8)
    corr=XAs.T@Zs/len(dev);corr=np.clip(corr,-1,1)
    best_pc=np.abs(corr).argmax(axis=1);best_r=corr[np.arange(len(candidate)),best_pc]
    candidate['best_image_pc']=best_pc;candidate['best_correlation']=best_r;candidate['best_abs_correlation']=np.abs(best_r)
    candidate=candidate.sort_values(['best_abs_correlation','score'],ascending=[False,False],kind='stable')
    candidate.to_csv(out/'phase9a_morphology_genes_DEVELOPMENT_ONLY.csv',index=False)
    # Phase9B/9C: gene symbols must be de-duplicated while preserving rank.
    sig=de[(de.fdr_bh<=.05)&(de.abs_cohen_d>=1.)]
    if len(sig)<100:sig=de.head(2000)
    def syms(df,maxn):return [s for s in df.gene_symbol.drop_duplicates().astype(str).tolist() if s and s.lower()!='nan'][:maxn]
    gbm=syms(sig[sig.direction=='GBM_high'],500)
    lgg=syms(sig[sig.direction=='LGG_high'],500)
    morph=syms(candidate,500)
    lists={'GBM_high_protein_coding':gbm,'LGG_high_protein_coding':lgg,'Morphology_linked_protein_coding':morph}
    for key,ls in lists.items():(out/f'phase9c_{key}_DEVELOPMENT_ONLY.txt').write_text('\n'.join(ls)+'\n')
    # Gene targets: original Phase11A top30 biomarker + top50 morph, unique.
    symbol_id={r.gene_symbol:r.gene_id for r in combined.itertuples() if r.gene_symbol and r.gene_symbol!='nan'}
    chosen=list(dict.fromkeys(syms(combined,30)+syms(candidate,50)))
    chosen=[s for s in chosen if s in symbol_id]
    defs={f'gene__{s}':[s] for s in chosen}
    # Three protein-coding programs are recomputed on development only.
    defs.update({f'program__{n}':syms for n,syms in lists.items() if len(syms)>=5})
    status='No GMT supplied: only training-derived gene targets and three data-derived programs; NOT equivalent to historical 23 pathways/programs.'
    if args.gmt:
        sets=load_gmt(args.gmt);database=[gm[g] for g in genes if gm[g]]
        enrich,extra=enriched_pathways_from_gmt(sets,lists,database,args.max_pathways)
        if not enrich.empty:enrich.to_csv(out/'phase9b_gmt_enrichment_DEVELOPMENT_ONLY.csv',index=False)
        defs.update(extra);status=f'GMT provided; {len(extra)} terms selected after development-only overrepresentation testing.'
    if args.enrichr:
        enrich,extra=enriched_pathways_from_enrichr(lists,args.max_pathways)
        enrich.to_csv(out/'phase9c_enrichr_DEVELOPMENT_ONLY.csv',index=False)
        defs.update(extra)
        status=f'Live Enrichr run using development-selected gene lists; {len(extra)} terms retained. Database release should be documented.'
    # Symbol mapping into annotated protein-coding ENSEMBL columns.
    symidx={gm[g]:i for i,g in enumerate(genes) if gm[g] in chosen or any(gm[g] in ls for ls in lists.values())}
    selected_defs={}
    for name,symlist in defs.items():
        inds=list(dict.fromkeys(symidx[s] for s in symlist if s in symidx))
        if (name.startswith('gene__') and len(inds)==1) or (not name.startswith('gene__') and len(inds)>=3):
            selected_defs[name]=inds
    # NOTE: Add GMT pathway symbols to symbol mapping as needed, not only dev lists.
    if args.gmt or args.enrichr:
        allsymbols={s for members in defs.values() for s in members}
        symidx={gm[g]:i for i,g in enumerate(genes) if gm[g] in allsymbols}
        selected_defs={name:list(dict.fromkeys(symidx[s] for s in ss if s in symidx)) for name,ss in defs.items()}
        selected_defs={n:v for n,v in selected_defs.items() if len(v)>=(1 if n.startswith('gene__') else 3)}
    if not selected_defs:raise ValueError('No valid targets selected')
    # Target programs standardized using DEV-PATIENT expression moments only.
    all_targets={};defs_metadata=[]
    for name,inds in selected_defs.items():
        if name.startswith('gene__'): val=E[:,inds[0]].astype(float)
        else:
            sc=StandardScaler().fit(E[dev][:,inds])
            val=sc.transform(E[:,inds]).mean(axis=1)
        all_targets[name]=val
        defs_metadata.append({'target':name,'gene_count':len(inds),'source':'development_only','genes':[genes[i] for i in inds]})
    targets=pd.DataFrame({'patient_id':ids,'split':ref.split,'project_id':ref.project_id,'y':y,**all_targets})
    targets.to_csv(out/'phase11a_target_matrix_DEVELOPMENT_FITTED.csv',index=False)
    write_json(out/'target_definitions_DEVELOPMENT_ONLY.json',defs_metadata)
    names=list(all_targets);Y=targets[names].to_numpy(dtype=float)
    # RidgeCV fits only on 583 development samples, never on 103 test observations.
    xsc=StandardScaler().fit(I[dev]);ysc=StandardScaler().fit(Y[dev]);Xd=xsc.transform(I[dev]);Xt=xsc.transform(I[te]);Yd=ysc.transform(Y[dev])
    rd=RidgeCV(alphas=[.1,1,10,100,1000],cv=5);rd.fit(Xd,Yd)
    predicted=ysc.inverse_transform(rd.predict(Xt))
    pcols={'patient_id':ids[te],'project_id':ref.project_id.iloc[te].to_numpy(),'y':y[te]}
    for j,n in enumerate(names): pcols[f'actual__{n}']=Y[te,j];pcols[f'pred__{n}']=predicted[:,j]
    pd.DataFrame(pcols).to_csv(out/'phase11a_fixed_test_predictions_CORRECTED.csv',index=False)
    rows=[]
    for j,name in enumerate(names):
        truth=Y[te,j];pr=predicted[:,j];ym=y[te]
        # Class-adjusted correlation: subtract test-class means for descriptive audit only.
        ca=truth.copy();cb=pr.copy()
        for c in (0,1):
            k=ym==c;ca[k]-=ca[k].mean();cb[k]-=cb[k].mean()
        rows.append({'target':name,'target_type':'gene' if name.startswith('gene__') else 'pathway_program',
             'n_test':len(te),'pearson_r':safe_corr(truth,pr),'class_adjusted_r':safe_corr(ca,cb),
             'within_gbm_r':safe_corr(truth[ym==1],pr[ym==1]),'within_lgg_r':safe_corr(truth[ym==0],pr[ym==0]),
             'mse':float(np.mean((truth-pr)**2)),'ridge_alpha':float(rd.alpha_)})
    m=pd.DataFrame(rows);m.to_csv(out/'phase11a_fixed_test_target_metrics_CORRECTED.csv',index=False)
    s=m.groupby('target_type').agg(n_targets=('target','size'),mean_pearson_r=('pearson_r','mean'),mean_class_adjusted_r=('class_adjusted_r','mean'),mean_within_gbm_r=('within_gbm_r','mean'),mean_within_lgg_r=('within_lgg_r','mean')).reset_index()
    s.to_csv(out/'Table_05_molecular_target_summary_CORRECTED.csv',index=False)
    fig,ax=plt.subplots(figsize=(7,4));x=np.arange(len(s));wid=.3
    ax.bar(x-wid/2,s.mean_pearson_r,width=wid,label='Overall Pearson r')
    ax.bar(x+wid/2,s.mean_class_adjusted_r,width=wid,label='Class-adjusted Pearson r')
    ax.set_xticks(x,s.target_type);ax.set_ylabel('Mean Pearson correlation');ax.set_ylim(-1,1);ax.legend();fig.tight_layout()
    fig.savefig(out/'Figure_04_CORRECTED_class_adjusted_comparison.png',dpi=210);plt.close(fig)
    provenance.update(status='COMPLETE',target_count=len(names),gene_count=sum(n.startswith('gene__') for n in names),
                      pathway_program_count=sum(not n.startswith('gene__') for n in names),pathway_status=status,
                      dev_count=len(dev),test_count=len(te),ridge_alpha=float(rd.alpha_),
                      caution='This canonical test was previously examined during the original study. Revised outputs are retrospective fixed-test re-evaluation, NOT untouched validation.')
    write_json(out/'manifest.json',provenance)
    print(status);print('COMPLETE:',out,flush=True)

if __name__=='__main__':main()
