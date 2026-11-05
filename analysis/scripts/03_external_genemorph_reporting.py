#!/usr/bin/env python3
"""Verify and report existing CPTAC & strict-LOO source outputs, do not refit externally."""
import argparse
from pathlib import Path
import pandas as pd
from nbv3_common import ensure_fresh_output, filehash, write_json

def main():
    a=argparse.ArgumentParser();a.add_argument('--project',default='.');a.add_argument('--run-id',required=True);args=a.parse_args()
    root=Path(args.project);out=ensure_fresh_output(root/'results'/'corrected_v3'/args.run_id/'external_and_retrieval')
    files={
     'rna':root/'results/external_validation/phase12a_v2_cptac_rna_harmonization/phase12a_v2_cptac_rna_harmonization_strategy_comparison.csv',
     'external':root/'results/external_validation/phase12d_final_consolidation/phase12d_final_external_validation_summary_table.csv',
     'loo':root/'results/genemorph_loo_rerun_20260818_final/loo_query_level_results.csv',
     'assertions':root/'results/genemorph_loo_rerun_20260818_final/self_exclusion_assertion_report.txt'}
    for k,p in files.items():
        if not p.is_file():raise FileNotFoundError(f'{k}: {p}')
    rna=pd.read_csv(files['rna']);ext=pd.read_csv(files['external']);loo=pd.read_csv(files['loo'])
    required={'strategy','n_external_samples','n_predicted_GBM_like'}
    if not required<=set(rna):raise ValueError(f'CPTAC RNA columns changed: {rna.columns.tolist()}')
    if len(loo)!=6 or 'loo_self_patch_count' not in loo or int(loo.loo_self_patch_count.sum())!=0:
        raise ValueError('Final Gene2Morph strict self-exclusion proof missing or inconsistent')
    if 'loo_top_source_patient' in loo and (loo.query_patient_id.astype(str)==loo.loo_top_source_patient.astype(str)).any():
        raise ValueError('Gene2Morph retrieved query patient as top-source; stop')
    rna['positive_recognition_rate']=rna.n_predicted_GBM_like/rna.n_external_samples
    rna.to_csv(out/'Supplementary_Table_S3_CPTAC_RNA_HARMONIZATION_EXPLORATORY.csv',index=False)
    ext.to_csv(out/'Supplementary_Table_S4_CPTAC_WSI_EXPLORATORY.csv',index=False)
    cols=[c for c in ['query_index','query_patient_id','query_class','loo_top_source_patient','loo_diagnosis_match','loo_self_patch_count','self_patch_candidates_excluded'] if c in loo]
    loo[cols].to_csv(out/'Supplementary_Table_S5_Gene2Morph_LOO_six_query.csv',index=False)
    n_match=int(loo.loo_diagnosis_match.fillna(False).astype(bool).sum())
    manuscript=f'''# External and reference retrieval — manuscript-safe reporting notes

**CPTAC RNA:** This external cohort contains GBM-positive patients only; report GBM-like recognition,
not balanced accuracy, specificity, or external GBM-versus-LGG discrimination. The published harmonization
strategy was selected after comparing GBM-positive recognition rates; it must be labeled **post hoc / exploratory**.
The five observed RNA processing strategies are recorded in `Supplementary_Table_S3...csv`.

**CPTAC WSI:** Direct patient-level transfer and later domain-robust reanalysis are distinct experiments.
The domain-robust result is a **post hoc sensitivity analysis**, not an independently frozen external test.
The original Phase 12D table is copied to `Supplementary_Table_S4...csv` without numeric alteration.

**Gene2Morph:** {len(loo)} previously selected query patients, {n_match}/{len(loo)} top-source diagnosis agreement,
with zero same-patient retrieved patches in the strict LOO rerun. This is **query-patient self-exclusion**,
not fully held-out independent retrieval: the reference bank includes other development/test patients and the
retrieval model was developed on the TCGA cohort. Figure 5 is a qualitative real-patch reference demonstration;
no RNA-to-image generation or clinical prediction is claimed.

**Figures 5 and 6:** Retain the verified original artwork if numerical labels correspond to saved tables.
Update legends, prose, and supplementary material rather than implying the exploratory analyses were prospective.
'''
    (out/'V3_methods_results_discussion_notes.md').write_text(manuscript)
    write_json(out/'manifest.json',{'status':'COMPLETE','source_sha256':{k:filehash(v) for k,v in files.items()},'n_queries':len(loo),'n_query_diagnosis_matches':n_match,
         'scientific_status':'Historical external and retrieval outputs only; no newly trained models or new external validation'})
    print('COMPLETE',out)
if __name__=='__main__':main()
