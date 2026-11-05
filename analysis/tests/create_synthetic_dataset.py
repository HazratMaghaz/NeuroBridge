"""Toy synthetic project for verifying model execution. NEVER publish these outputs."""
import argparse
from pathlib import Path
import numpy as np,pandas as pd
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
root=Path(a.out);gen=np.random.default_rng(42)
n=320;n_gene=180;y=np.array([0]*224+[1]*96);gen.shuffle(y)
ids=[f'TCGA-XX-{i:04d}' for i in range(n)]
perm=gen.permutation(n)
split=np.array(['']*n,dtype=object);split[perm[:220]]='train';split[perm[220:270]]='val';split[perm[270:]]='test'
labels=np.where(y==1,'TCGA-GBM','TCGA-LGG')
E=gen.normal(size=(n,n_gene)).astype('float32');E[:,:35]+=(y*1.5)[:,None]
I=gen.normal(size=(n,768)).astype('float32');I[:,:28]+=(y*1.1)[:,None]
for f in ['metadata','data/expression/processed','features/ctranspath_7B_wsi_streaming_full']:(root/f).mkdir(parents=True,exist_ok=True)
pd.DataFrame({'patient_id':ids,'project_id':labels,'split':split}).to_csv(root/'metadata/phase6b_patient_splits.csv',index=False)
genes=[f'ENSG{i:011d}' for i in range(1,n_gene+1)]
df=pd.DataFrame(E,columns=genes);df.insert(0,'patient_id',ids)
df.to_csv(root/'data/expression/processed/expression_matrix_log2_tpm_filtered.csv',index=False)
pd.DataFrame({'gene_id_clean':genes,'gene_name':[f'GENE{i}' for i in range(n_gene)],'gene_type':['protein_coding']*n_gene}).to_csv(root/'data/expression/processed/expression_gene_annotation.csv',index=False)
im=pd.DataFrame(I,columns=[f'ctranspath_feat_{i:03d}' for i in range(768)]);im.insert(0,'patient_id',ids)
im.to_csv(root/'features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv',index=False)
print('Generated toy data, NOT real NeuroBridge cohort',root)
