#!/usr/bin/env python3
"""Refuse to call a V3 run ready until corrected classification/biology/external analyses exist."""
import argparse,zipfile
from pathlib import Path
import pandas as pd
from nbv3_common import filehash,write_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',default='.');p.add_argument('--run-id',required=True);p.add_argument('--demo',action='store_true',help='Toy data validation ONLY; forbids manuscript interpretation');args=p.parse_args()
    base=Path(args.project)/'results'/'corrected_v3'/args.run_id
    needed=[base/'classification'/'development_cv_raw.csv',base/'classification'/'development_cv_summary.csv',
        base/'classification'/'canonical_test_metrics.csv',base/'classification'/'manifest.json',
        base/'biology'/'phase11a_fixed_test_target_metrics_CORRECTED.csv',base/'biology'/'Table_05_molecular_target_summary_CORRECTED.csv',
        base/'biology'/'manifest.json',base/'external_and_retrieval'/'manifest.json']
    absent=[str(x) for x in needed if not x.exists()]
    if absent:raise FileNotFoundError('Cannot release incomplete correction. Missing:\n'+'\n'.join(absent))
    cls=pd.read_csv(base/'classification'/'canonical_test_metrics.csv')
    mol=pd.read_csv(base/'biology'/'phase11a_fixed_test_target_metrics_CORRECTED.csv')
    cv=pd.read_csv(base/'classification'/'development_cv_raw.csv')
    if 'n' not in cls or not (cls['n']>0).all():raise ValueError('Missing test counts')
    if not args.demo and (cls['n'].min()!=103 or cls['n'].max()!=103):raise ValueError('Canonical fixed-test count must be 103')
    if not args.demo and (mol.n_test!=103).any():raise ValueError('Biology fixed test not 103')
    if not cv.evaluation.str.startswith('cv_fold_').all():raise ValueError('CV source was not development folds')
    if set(cls.scenario)!=set(cv.scenario):raise ValueError('CV and fixed-test scenario mismatch')
    import json
    manifests={key:json.loads((base/key/'manifest.json').read_text()) for key in ['classification','biology','external_and_retrieval']}
    if any(d.get('status')!='COMPLETE' for d in manifests.values()):raise RuntimeError('Incomplete stage manifest found')
    if args.demo and not manifests['classification']['settings']['demo']:raise RuntimeError('Cannot package real run using --demo')
    if not args.demo and manifests['classification']['settings']['demo']:raise RuntimeError('Cannot package synthetic run as real')
    files=[f for f in base.rglob('*') if f.is_file() and f.suffix in {'.csv','.json','.png','.md'}]
    archive=base.parent/(args.run_id+'_REVIEW_BUNDLE.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):z.write(f,arcname=str(f.relative_to(base)))
    write_json(base/'REVIEW_READY.json',{'status':'REVIEW_READY_NOT_YET_MANUSCRIPT_APPROVED','archive':str(archive),
          'files':len(files),'sha256':{str(f.relative_to(base)):filehash(f) for f in files},
          'note':'Do not paste into manuscript before independent statistical/biological review.',
          'synthetic_demo':args.demo})
    print('VALIDATION PASSED. Review bundle:',archive)
if __name__=='__main__':main()
