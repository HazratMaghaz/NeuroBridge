"""NeuroBridge V3 shared, deliberately strict data loading and audit helpers."""
from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
    confusion_matrix, f1_score, roc_auc_score)

EXPR='data/expression/processed/expression_matrix_log2_tpm_filtered.csv'
SPLITS=os.environ.get('NEUROBRIDGE_SPLITS_CSV', 'metadata/phase6b_patient_splits.csv')
IMG='features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv'
ANNO='data/expression/processed/expression_gene_annotation.csv'
ALLOWED={'train','val','test'}

def filehash(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,default=str)+'\n')

def ordered_feature_cols(df,pattern,dim):
    pairs=[]
    for c in df.columns:
        m=re.fullmatch(pattern,str(c))
        if m and pd.api.types.is_numeric_dtype(df[c]): pairs.append((int(m.group(1)),c))
    pairs.sort()
    if len(pairs)==dim and [x[0] for x in pairs]==list(range(dim)):
        return [c for _,c in pairs]
    raise ValueError(f'Expected exactly {dim} ordered features matching {pattern}. Found {len(pairs)}. Example {pairs[:4]}')

def load_dataset(project, demo=False):
    root=Path(project)
    split_path=Path(SPLITS)
    if not split_path.is_absolute(): split_path=root/split_path
    paths={'expression':root/EXPR,'image':root/IMG,'split':split_path}
    for name,p in paths.items():
        if not p.is_file(): raise FileNotFoundError(f'{name}: {p}')
    split=pd.read_csv(paths['split']); expr=pd.read_csv(paths['expression']); img=pd.read_csv(paths['image'])
    for name,df in [('split',split),('expression',expr),('image',img)]:
        if 'patient_id' not in df: raise ValueError(f'{name} missing patient_id')
        df['patient_id']=df['patient_id'].astype(str).str.strip()
        if df.patient_id.duplicated().any(): raise ValueError(f'Duplicate {name} patient IDs')
    if 'split' not in split: raise ValueError('Missing canonical split column')
    split['split']=split['split'].astype(str).str.strip().str.lower()
    if not set(split['split'])<=ALLOWED: raise ValueError('Unexpected split labels')
    if 'project_id' not in split:
        if 'project_id' not in expr: raise ValueError('Project labels missing from both split and expression')
        split=split.merge(expr[['patient_id','project_id']],on='patient_id',validate='one_to_one')
    lbl={'TCGA-LGG':0,'TCGA-GBM':1}
    if not set(split.project_id.unique())<=set(lbl): raise ValueError('Unexpected project_id label')
    split['y']=split.project_id.map(lbl).astype(int)
    if 'project_id' in expr.columns:
        chk=split[['patient_id','project_id']].merge(expr[['patient_id','project_id']],on='patient_id',suffixes=('_split','_expr'))
        if (chk.project_id_split!=chk.project_id_expr).any(): raise ValueError('Conflicting expression labels')
    gene_cols=[c for c in expr.columns if re.fullmatch(r'ENSG\d+(?:\.\d+)?',str(c)) and pd.api.types.is_numeric_dtype(expr[c])]
    if len(gene_cols)<10: raise ValueError(f'Only {len(gene_cols)} numeric ENSG gene columns detected. Refuse fallback to metadata')
    try: image_cols=ordered_feature_cols(img,r'(?:ctranspath_feat_|ctranspath_|img_feat_)(\d+)',768)
    except ValueError:
        raise ValueError('Image feature columns must have index 0..767 and ctranspath_feat_/ctranspath_/img_feat_ prefix; inspect your file header')
    ref=split[['patient_id','project_id','split','y']].sort_values('patient_id').reset_index(drop=True)
    if len(ref)!=len(expr) or len(ref)!=len(img) or set(ref.patient_id)!=set(expr.patient_id) or set(ref.patient_id)!=set(img.patient_id):
        raise ValueError('Strict patient set mismatch among split, expression and CTransPath; no silent inner join')
    if not demo and (len(ref)!=686 or ref.split.value_counts().to_dict()!={'train':480,'val':103,'test':103} or int(ref.y.sum())!=195):
        raise ValueError(f'Unexpected canonical cohort counts: {len(ref)}, {ref.split.value_counts().to_dict()}, GBM={ref.y.sum()}; use --demo ONLY for synthetic tests')
    xexpr=ref[['patient_id']].merge(expr[['patient_id']+gene_cols],on='patient_id',validate='one_to_one')
    ximg=ref[['patient_id']].merge(img[['patient_id']+image_cols],on='patient_id',validate='one_to_one')
    E=xexpr[gene_cols].to_numpy(dtype=np.float32); I=ximg[image_cols].to_numpy(dtype=np.float32)
    if not np.isfinite(E).all() or not np.isfinite(I).all(): raise ValueError('NaN/Inf found in input; resolve before training')
    return ref, E, I, gene_cols, paths

def metrics(y,p,s,**extra):
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    d={'n':len(y),'accuracy':accuracy_score(y,p),'balanced_accuracy':balanced_accuracy_score(y,p),
       'f1_gbm':f1_score(y,p,zero_division=0), 'tn_lgg':int(tn),'fp_lgg_as_gbm':int(fp),
       'fn_gbm_as_lgg':int(fn),'tp_gbm':int(tp),'sensitivity_gbm':tp/max(1,tp+fn),
       'specificity_lgg':tn/max(1,tn+fp),'roc_auc':roc_auc_score(y,s) if len(np.unique(y))==2 else float('nan'),
       'pr_auc':average_precision_score(y,s) if len(np.unique(y))==2 else float('nan')}
    d.update(extra);return d

def ensure_fresh_output(output):
    out=Path(output)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f'Refusing to overwrite existing results directory: {out}; choose a new --run-id')
    out.mkdir(parents=True,exist_ok=True)
    return out
