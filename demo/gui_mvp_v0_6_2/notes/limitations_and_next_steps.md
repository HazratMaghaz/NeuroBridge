# Limitations and Next Steps

## Current Limitations
- **Not a Pan-CNS Classifier:** The model is strictly focused on distinguishing adult-type diffuse gliomas (GBM-like vs. LGG-like). It has not been trained on or calibrated for ependymomas, medulloblastomas, or pediatric tumors.
- **Predicted vs. Measured:** The outputs are a predicted gene-expression-like matrix. While it correlates with true biological state, it is **not measured RNA-seq**. Outliers or extremely rare mutational profiles may yield inaccurate histological extrapolations.
- **External Validation:** While internally robust, the model requires broader external validation on completely independent institutional cohorts to confirm cross-site generalization.
- **WSI Upload Restrictions:** Currently, WSI inference relies on absolute local file paths to bypass browser limitations. While this is safer for massive `.svs` files, it limits accessibility for entirely remote users without filesystem access.

## Next Steps
1. **Survival Analysis Integration:** If clinical metadata is available, integrate survival predictions, Kaplan-Meier (KM) curves, and c-index metrics into the output reports to demonstrate direct clinical utility.
2. **Supervisor Feedback:** Secure detailed feedback from the supervisor on the current GUI layout and matrix formatting before transitioning into the final thesis writing phase.
3. **Web-based WSI Uploads:** In future iterations (post-MVP), implement chunked, multi-part browser uploads to allow remote users to process WSI files without local path access.
