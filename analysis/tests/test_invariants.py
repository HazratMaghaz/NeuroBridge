"""Fast reproducibility/split invariants. Run: python -m unittest discover -s tests"""
import importlib.util,sys,unittest
from pathlib import Path
import numpy as np
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPT))

def import_script(filename,name):
    sp=importlib.util.spec_from_file_location(name,SCRIPT/filename)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    return mod
C=import_script('01_corrected_classification.py','nbv3_classification')
B=import_script('02_corrected_biology.py','nbv3_biology')

class LeakageInvariants(unittest.TestCase):
    def test_pca_does_not_fit_eval_patients(self):
        rng=np.random.default_rng(8)
        E=rng.normal(size=(90,35)).astype('float32')
        a,b=np.arange(55),np.arange(55,90)
        A1,B1,info=C.build_molecular(E,a,b,10,20,42)
        changed=E.copy();changed[b]*=10000;changed[b]+=12345
        A2,B2,info2=C.build_molecular(changed,a,b,10,20,42)
        self.assertTrue(np.allclose(A1,A2,atol=1e-5))
        self.assertFalse(np.allclose(B1,B2))
        self.assertEqual(info['scaler_n'],len(a))
    def test_pca_overlap_guard(self):
        with self.assertRaises(ValueError):C.build_molecular(np.ones((10,5)),[0,1,2],[2,3],2,4,42)
    def test_all_scenarios_declared(self):
        self.assertEqual(len(C.SCENARIOS),8)
        self.assertEqual(len(C.CORE),6)
    def test_bh_monotonic_in_sorted_p(self):
        p=np.array([.03,.003,.0001,.2,.8]);q=B.bh(p)
        order=np.argsort(p)
        self.assertTrue(np.all(np.diff(q[order])>=-1e-12))
    def test_class_adjusted_constant_returns_nan(self):
        self.assertTrue(np.isnan(B.safe_corr(np.ones(10),np.arange(10))))

if __name__=='__main__':unittest.main()
