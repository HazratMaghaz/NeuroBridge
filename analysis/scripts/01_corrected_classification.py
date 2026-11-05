#!/usr/bin/env python3
"""Fold-isolated molecular PCA-128 + MLP-64 + mapped-modality classification.

Purposely never reads historic PCA/latent/prediction CSVs. This is a NEW validation
protocol, not an exact rerun of 08A/08D. Test = historical 103-patient fixed test.
"""
from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.cross_decomposition import PLSRegression
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import RepeatedStratifiedKFold, KFold, train_test_split
from nbv3_common import load_dataset, metrics, ensure_fresh_output, filehash, write_json, ordered_feature_cols

SCENARIOS=['true_image_only','true_molecular_only','true_image_plus_true_molecular',
  'image_available_predicted_molecular','molecular_available_predicted_image',
  'predicted_molecular_only','predicted_image_only',
  'predicted_image_plus_predicted_molecular']

RESNET='embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv'
CORE=['image_resnet50','image_ctranspath','image_fused_resnet_ctranspath','molecular_pca128',
      'molecular_supervised_mlp64','fusion_ctranspath_supervised_mlp64']

def load_resnet_features(project,ref,demo_skip=False):
    p=Path(project)/RESNET
    if not p.is_file():
        if demo_skip:return None,None
        raise FileNotFoundError(f'ResNet50 patient embeddings required for complete Figure 2: {p}; --skip-resnet allowed only with --demo')
    df=pd.read_csv(p)
    df['patient_id']=df['patient_id'].astype(str).str.strip()
    if df.patient_id.duplicated().any() or set(df.patient_id)!=set(ref.patient_id):
        raise ValueError('ResNet patient IDs not 1-to-1 aligned with canonical cohort')
    errors=[]
    for prefix in [r'img_feat_(\d+)',r'resnet50_mean_(\d+)',r'resnet50_feat_(\d+)']:
        try:cols=ordered_feature_cols(df,prefix,2048);break
        except ValueError as e:errors.append(str(e))
    else:raise ValueError('ResNet-50 must have 2048 indexed columns. '+str(errors))
    arr=ref[['patient_id']].merge(df[['patient_id']+cols],on='patient_id',validate='one_to_one')[cols].to_numpy(dtype=np.float32)
    if not np.isfinite(arr).all():raise ValueError('Invalid ResNet features')
    return arr,p

def init_seed(s):
    random.seed(s);np.random.seed(s)
    import torch
    torch.manual_seed(s)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(s)

def build_molecular(E,fit_idx,apply_idx,pca_dim,topvar,seed):
    """No fitting on apply_idx; includes top variance and scaler inside the fold."""
    if set(fit_idx)&set(apply_idx): raise ValueError('PCA fit and evaluation indices overlap')
    var=E[fit_idx].var(axis=0)
    n=min(topvar,E.shape[1]); top=np.argsort(-var,kind='stable')[:n]
    scaler=StandardScaler()
    Xtr=scaler.fit_transform(E[fit_idx][:,top])
    Xte=scaler.transform(E[apply_idx][:,top])
    dim=min(pca_dim,len(fit_idx)-1,Xtr.shape[1])
    if dim<2: raise ValueError('Too few training patients for PCA')
    pca=PCA(n_components=dim,svd_solver='randomized',random_state=seed)
    A=pca.fit_transform(Xtr).astype(np.float32)
    B=pca.transform(Xte).astype(np.float32)
    return A,B,{'top_genes_count':n,'pca_dim':dim,'scaler_n':int(scaler.n_samples_seen_),'top_gene_indices':top.tolist()}

class SupervisedMolecularMLP:
    def __init__(self,dim,dropout=.20):
        import torch.nn as nn
        self.nn=nn
        self.encoder=nn.Sequential(nn.Linear(dim,256),nn.BatchNorm1d(256),nn.ReLU(),nn.Dropout(dropout),
                                   nn.Linear(256,128),nn.BatchNorm1d(128),nn.ReLU(),nn.Dropout(dropout),nn.Linear(128,64))
        self.classifier=nn.Sequential(nn.ReLU(),nn.Dropout(dropout),nn.Linear(64,2))
        self.model=nn.Sequential(self.encoder,self.classifier)
    def to(self,device): self.model.to(device);return self
    def encode(self,X,device):
        import torch
        self.model.eval()
        with torch.no_grad():
            return self.encoder(torch.tensor(X,dtype=torch.float32,device=device)).cpu().numpy()

def train_mlp(X,y,epochs,patience,seed,device):
    """Inner early-stopping split is carved ONLY from the supplied outer-fit patients.
    Final embedding model trained on whole outer-fit with selected epoch count.
    """
    import torch
    from torch import nn
    from torch.utils.data import DataLoader,TensorDataset
    init_seed(seed)
    ia,ib=train_test_split(np.arange(len(y)),test_size=.15,random_state=seed,stratify=y)
    model=SupervisedMolecularMLP(X.shape[1]).to(device)
    optimizer=torch.optim.Adam(model.model.parameters(),lr=1e-3,weight_decay=1e-4)
    counts=np.bincount(y[ia],minlength=2)
    cw=torch.tensor(len(ia)/(2*np.maximum(counts,1)),dtype=torch.float32,device=device)
    lossfn=nn.CrossEntropyLoss(weight=cw)
    data=TensorDataset(torch.from_numpy(X[ia]),torch.from_numpy(y[ia]).long())
    loader=DataLoader(data,batch_size=min(64,len(ia)),shuffle=True,drop_last=False)
    xval=torch.tensor(X[ib],dtype=torch.float32,device=device)
    yval=y[ib]
    from sklearn.metrics import balanced_accuracy_score
    best_loss=float('inf');best_ba=0.0;left=patience;best_epoch=1
    for ep in range(1,epochs+1):
        model.model.train()
        for xb,yb in loader:
            xb=xb.to(device);yb=yb.to(device)
            optimizer.zero_grad();loss=lossfn(model.model(xb),yb);loss.backward();optimizer.step()
        model.model.eval()
        with torch.no_grad():
            logits=model.model(xval)
            p=logits.argmax(1).cpu().numpy()
            val_loss=float(lossfn(logits,torch.tensor(yval,dtype=torch.long,device=device)).item())
        score=balanced_accuracy_score(yval,p);best_ba=max(best_ba,float(score))
        if val_loss<best_loss-1e-5: best_loss=val_loss;best_epoch=ep;left=patience
        else: left-=1
        if left<=0: break
    # After development-only epoch selection, fit encoder on ALL outer-fit patients.
    init_seed(seed)
    model=SupervisedMolecularMLP(X.shape[1]).to(device)
    cw=torch.tensor(len(y)/(2*np.maximum(np.bincount(y,minlength=2),1)),dtype=torch.float32,device=device)
    lossfn=nn.CrossEntropyLoss(weight=cw)
    optimizer=torch.optim.Adam(model.model.parameters(),lr=1e-3,weight_decay=1e-4)
    full=DataLoader(TensorDataset(torch.from_numpy(X),torch.from_numpy(y).long()),batch_size=min(64,len(y)),shuffle=True,drop_last=False)
    for ep in range(best_epoch):
        model.model.train()
        for xb,yb in full:
            xb=xb.to(device);yb=yb.to(device)
            optimizer.zero_grad();loss=lossfn(model.model(xb),yb);loss.backward();optimizer.step()
    return model,{'selected_epochs':best_epoch,'inner_validation_best_ba':float(best_ba),'inner_validation_min_loss':float(best_loss),'inner_n':len(ib)}

def mapped_predictions(Itr,Ite,Ztr,Zte,seed,img_to_mol,n_oof_folds=3):
    """Cross-fitted mapping predictions for outer training cases; fully fitted mapper
    for evaluation cases. Avoids training classifier on in-sample mapping predictions.
    """
    def make_image_to_mol(k):
        if img_to_mol=='ridge':return make_pipeline(StandardScaler(),Ridge(alpha=10.0))
        return make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(256,128),alpha=1e-3,
                 learning_rate_init=1e-3,max_iter=1000,early_stopping=True,random_state=k))
    def make_mol_to_image(Z,I):
        xs=StandardScaler().fit(Z);ys=StandardScaler().fit(I)
        dim=min(32,Z.shape[1],I.shape[1],len(Z)-1)
        model=PLSRegression(n_components=dim,scale=False)
        model.fit(xs.transform(Z),ys.transform(I))
        return (xs,ys,model)
    def pred_image(models,z):
        xs,ys,pls=models
        return ys.inverse_transform(pls.predict(xs.transform(z)))
    oof_mol=np.zeros_like(Ztr)
    oof_img=np.zeros_like(Itr)
    kfold=KFold(n_splits=n_oof_folds,shuffle=True,random_state=seed)
    for index,(a,b) in enumerate(kfold.split(Itr)):
        im=make_image_to_mol(seed+index);im.fit(Itr[a],Ztr[a]);oof_mol[b]=im.predict(Itr[b])
        models=make_mol_to_image(Ztr[a],Itr[a]);oof_img[b]=pred_image(models,Ztr[b])
    final_im=make_image_to_mol(seed);final_im.fit(Itr,Ztr)
    final_mol=make_mol_to_image(Ztr,Itr)
    return oof_mol,final_im.predict(Ite),oof_img,pred_image(final_mol,Zte)

def scenario_arrays(Itr,Ite,Ztr,Zte,Pmol_tr,Pmol_te,Pimg_tr,Pimg_te):
    return {
      'true_image_only':(Itr,Ite),
      'true_molecular_only':(Ztr,Zte),
      'true_image_plus_true_molecular':(np.hstack([Itr,Ztr]),np.hstack([Ite,Zte])),
      'image_available_predicted_molecular':(np.hstack([Itr,Pmol_tr]),np.hstack([Ite,Pmol_te])),
      'molecular_available_predicted_image':(np.hstack([Ztr,Pimg_tr]),np.hstack([Zte,Pimg_te])),
      'predicted_molecular_only':(Pmol_tr,Pmol_te),
      'predicted_image_only':(Pimg_tr,Pimg_te),
      'predicted_image_plus_predicted_molecular':(np.hstack([Pimg_tr,Pmol_tr]),np.hstack([Pimg_te,Pmol_te])),
    }

def run_split(ref,E,I,R,fit_indices,eval_indices,args,seed,split_name):
    assert not set(fit_indices)&set(eval_indices)
    y=ref.y.to_numpy();ids=ref.patient_id.to_numpy()
    A,B,prep=build_molecular(E,fit_indices,eval_indices,args.pca_dim,args.topvar,seed)
    enc,mlpinfo=train_mlp(A,y[fit_indices],args.epochs,args.patience,seed,args.device)
    Ztr=enc.encode(A,args.device);Zte=enc.encode(B,args.device)
    Itr=I[fit_indices];Ite=I[eval_indices]
    Pmol_tr,Pmol_te,Pimg_tr,Pimg_te=mapped_predictions(Itr,Ite,Ztr,Zte,seed,args.img_to_mol,args.mapping_oof_folds)
    xs=scenario_arrays(Itr,Ite,Ztr,Zte,Pmol_tr,Pmol_te,Pimg_tr,Pimg_te)
    rows=[]; preds=[]
    for scenario,(Xtr,Xte) in xs.items():
        clf=make_pipeline(StandardScaler(),LogisticRegression(max_iter=5000,class_weight='balanced',solver='liblinear',random_state=seed))
        clf.fit(Xtr,y[fit_indices]);p=clf.predict(Xte);prob=clf.predict_proba(Xte)[:,1]
        rows.append(metrics(y[eval_indices],p,prob,scenario=scenario,model='logreg_balanced',evaluation=split_name,
                            n_train=len(fit_indices),pca_dim=prep['pca_dim'],mlp_epochs=mlpinfo['selected_epochs']))
        preds.extend([{'patient_id':str(pid),'scenario':scenario,'evaluation':split_name,'y_true':int(yt),'y_pred':int(yp),'prob_gbm':float(sc)}
                      for pid,yt,yp,sc in zip(ids[eval_indices],y[eval_indices],p,prob)])
    core_vectors={'image_ctranspath':(Itr,Ite),'molecular_pca128':(A,B),
      'molecular_supervised_mlp64':(Ztr,Zte),
      'fusion_ctranspath_supervised_mlp64':(np.hstack([Itr,Ztr]),np.hstack([Ite,Zte]))}
    if R is not None:
        core_vectors.update({'image_resnet50':(R[fit_indices],R[eval_indices]),
            'image_fused_resnet_ctranspath':(np.hstack([R[fit_indices],Itr]),np.hstack([R[eval_indices],Ite]))})
    core_rows=[]
    for group,(ct,ce) in core_vectors.items():
        model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=5000,class_weight='balanced',solver='liblinear',random_state=seed))
        model.fit(ct,y[fit_indices]);pp=model.predict(ce);ss=model.predict_proba(ce)[:,1]
        core_rows.append(metrics(y[eval_indices],pp,ss,representation=group,evaluation=split_name,n_train=len(fit_indices)))
    info={'evaluation':split_name,'fit_patient_hash':hash_patient_ids(ids[fit_indices]),'eval_patient_hash':hash_patient_ids(ids[eval_indices]),
          'fit_n':len(fit_indices),'eval_n':len(eval_indices),'preprocessing':{k:v for k,v in prep.items() if k!='top_gene_indices'},
          'early_stopping':mlpinfo,'mapper_img_to_mol':args.img_to_mol,'mapper_mol_to_img':'PLSRegression(32_max)','mapping_train_predictions':'KFold out-of-fold'}
    return rows,preds,info,core_rows

def hash_patient_ids(ids):
    import hashlib
    return hashlib.sha256('\n'.join(sorted(map(str,ids))).encode()).hexdigest()

def plot_figures(cv,canonical,core,core_cv,out):
    # Show development-only repeated-CV and the historical fixed-test re-evaluation together.
    def panel(df,cvdf,key,filename,title):
        s=cvdf.groupby(key).balanced_accuracy.agg(['mean','std']).reset_index()
        s=df[[key,'balanced_accuracy']].merge(s,on=key,how='left').sort_values('balanced_accuracy')
        y=np.arange(len(s));fig,ax=plt.subplots(figsize=(10,max(4,.52*len(s)+1)))
        ax.barh(y-.19,s.balanced_accuracy*100,height=.36,label='Fixed test: 103 cases')
        ax.barh(y+.19,s['mean']*100,xerr=s['std'].fillna(0)*100,capsize=2,height=.36,
                alpha=.68,label='Development-only CV (mean ± SD)')
        ax.set_yticks(y,s[key]);ax.set_xlabel('Balanced accuracy (%)');ax.set_xlim(0,101)
        ax.set_title(title);ax.legend(loc='lower right');fig.tight_layout()
        fig.savefig(out/filename,dpi=210);plt.close(fig)
        return s
    d=panel(core,core_cv,'representation','Figure_02_CORRECTED_core_performance.png','V3 corrected core model performance')
    d.to_csv(out/'Figure_02_CORRECTED_source_data.csv',index=False)
    keep=canonical[canonical.scenario.ne('predicted_image_plus_predicted_molecular')]
    joined=panel(keep,cv[cv.scenario.ne('predicted_image_plus_predicted_molecular')],
           'scenario','Figure_03_CORRECTED_missing_modality.png','V3 corrected missing-modality performance')
    joined.to_csv(out/'Figure_03_CORRECTED_source_data.csv',index=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',default='.');ap.add_argument('--run-id',required=True)
    ap.add_argument('--cv-folds',type=int,default=5);ap.add_argument('--cv-repeats',type=int,default=3)
    ap.add_argument('--epochs',type=int,default=150);ap.add_argument('--patience',type=int,default=20)
    ap.add_argument('--pca-dim',type=int,default=128);ap.add_argument('--topvar',type=int,default=5000)
    ap.add_argument('--img-to-mol',choices=['ridge','mlp'],default='ridge')
    ap.add_argument('--mapping-oof-folds',type=int,default=3)
    ap.add_argument('--device',choices=['cpu','cuda'],default='cpu');ap.add_argument('--demo',action='store_true')
    ap.add_argument('--skip-resnet',action='store_true',help='Synthetic/demo only; full V3 requires ResNet-50 file')
    args=ap.parse_args()
    if args.skip_resnet and not args.demo:raise ValueError('--skip-resnet allowed only for synthetic demo')
    import torch
    if args.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA requested but torch.cuda.is_available() false')
    ref,E,I,genes,paths=load_dataset(args.project,demo=args.demo)
    R,rpath=load_resnet_features(args.project,ref,demo_skip=args.skip_resnet)
    root=Path(args.project)/'results'/'corrected_v3'/args.run_id
    out=ensure_fresh_output(root/'classification')
    dev=np.flatnonzero(ref.split.isin(['train','val'])); test=np.flatnonzero(ref.split.eq('test'))
    assert not set(dev)&set(test)
    manifest={'status':'RUNNING','protocol':'2026-10-19 corrected V3 retrospective re-evaluation', 'settings':vars(args),
              'source_hashes':{**{k:filehash(v) for k,v in paths.items()},**({'resnet':filehash(rpath)} if rpath else {})},
              'development_count':len(dev),'test_count':len(test),'development_patient_hash':hash_patient_ids(ref.patient_id.iloc[dev]),
              'test_patient_hash':hash_patient_ids(ref.patient_id.iloc[test]),
              'caution':'Prior manuscripts examined the canonical 103 test patients; this is retrospective fixed-test re-evaluation, not an untouched prospective test.',
              'new_mapper_note':'Image->molecular estimator is explicitly configured. Default ridge differs from Phase 8B selected MLP; compare as a newly specified protocol.',
              'zero_input_scenario_warning':'predicted_image_plus_predicted_molecular is NOT a valid missing-both-modality inference scenario; use only as a research reconstruction scenario.'}
    write_json(out/'manifest.json',manifest)
    cv=RepeatedStratifiedKFold(n_splits=args.cv_folds,n_repeats=args.cv_repeats,random_state=42)
    records=[]; allpred=[]; info=[];core_records=[]
    for k,(a,b) in enumerate(cv.split(E[dev],ref.y.iloc[dev]),1):
        tr,va=dev[a],dev[b]
        if set(va)&set(test) or set(tr)&set(test):raise AssertionError('Test leaked into CV')
        print(f'CV {k}/{args.cv_folds*args.cv_repeats}: outer fit {len(tr)}, outer validation {len(va)}',flush=True)
        rows,preds,meta,cores=run_split(ref,E,I,R,tr,va,args,42+k,f'cv_fold_{k:02d}')
        records.extend(rows);allpred.extend(preds);info.append(meta);core_records.extend(cores)
        pd.DataFrame(records).to_csv(out/'development_cv_raw.csv',index=False)
        pd.DataFrame(allpred).to_csv(out/'development_cv_predictions.csv',index=False)
    print('Fixed-test re-evaluation (test labels accessed ONLY after development protocol fixed)',flush=True)
    rows,preds,meta,cores=run_split(ref,E,I,R,dev,test,args,42042,'canonical_test')
    pd.DataFrame(rows).to_csv(out/'canonical_test_metrics.csv',index=False)
    pd.DataFrame(preds).to_csv(out/'canonical_test_predictions.csv',index=False)
    info.append(meta)
    pd.DataFrame(cores).to_csv(out/'core_canonical_test_metrics.csv',index=False)
    pd.DataFrame(core_records).to_csv(out/'core_development_cv_raw.csv',index=False)
    core_summary=pd.DataFrame(core_records).groupby('representation').agg(balanced_accuracy_mean=('balanced_accuracy','mean'),balanced_accuracy_std=('balanced_accuracy','std'),fold_count=('balanced_accuracy','size')).reset_index()
    core_summary.to_csv(out/'core_development_cv_summary.csv',index=False)
    summary=pd.DataFrame(records).groupby('scenario').agg(balanced_accuracy_mean=('balanced_accuracy','mean'),balanced_accuracy_std=('balanced_accuracy','std'),roc_auc_mean=('roc_auc','mean'),fold_count=('balanced_accuracy','size')).reset_index()
    summary.to_csv(out/'development_cv_summary.csv',index=False)
    write_json(out/'fold_provenance.json',info)
    plot_figures(pd.DataFrame(records),pd.DataFrame(rows),pd.DataFrame(cores),pd.DataFrame(core_records),out)
    manifest['status']='COMPLETE';manifest['outputs']='classification (8 scenarios)';write_json(out/'manifest.json',manifest)
    print('COMPLETE',out,flush=True)

if __name__=='__main__':main()
