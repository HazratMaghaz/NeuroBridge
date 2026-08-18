# 5-Minute Supervisor Demo Script

## 1. Setup & First Click (0:00 - 1:00)
- **Action:** Open the dashboard and show the **Backend Status Indicator** (should be green/connected).
- **Explanation:** "This is the unified CNS-MultiModalAI frontend. It successfully bridges our Python machine learning backend with a modern, responsive web interface. The backend is running securely on the local machine."

## 2. RNA Workflow (1:00 - 2:00)
- **Action:** Click the **RNA → Morphology** tab. Run a sample `test_rna.csv`.
- **Explanation:** "First, we demonstrate the molecular-to-image direction. We upload a patient's RNA-seq expression matrix. The Phase 14 model processes this to yield a GBM-like versus LGG-like classification score. We also demonstrate the 'Morphology Canvas' which retrieves and displays the histological patches that the model associates with this specific transcriptional profile."

## 3. Patch / Image Workflow (2:00 - 3:00)
- **Action:** Switch to the **Patch / Image → Molecular** tab. Upload a `patches.zip`.
- **Explanation:** "Now we demonstrate the reverse: image-to-molecular inference. The user uploads pre-extracted histology patches. The backend generates 768-dimensional CTransPath embeddings and feeds them into our frozen Phase 15G model. This avoids exposing the end-user to raw Python scripts while standardizing the pipeline."

## 4. WSI Local-Path Workflow (3:00 - 4:00)
- **Action:** Switch to the **WSI Analysis** tab. Input an absolute path to a local `.svs` file (e.g., `/path/to/data/example.svs`) and set max patches to 20.
- **Explanation:** "For realistic pathology workflows, requiring ZIPs is cumbersome. We implemented a 'Local WSI Path' mode. The backend uses OpenSlide to automatically mask tissue, randomly sample diagnostic regions, and extract patches in real-time. This is highly scalable and completely bypasses browser file-size upload limits."

## 5. Explaining the Output Matrices (4:00 - 5:00)
- **Action:** Scroll down to the WSI or Patch Results. Expand the "Main Results" downloads and point out the matrices.
- **Explanation:** "The most critical scientific output here is the **Predicted Gene / Pathway Expression Matrix**. Based purely on the H&E image embeddings, the model computationally predicts expression levels for 101 distinct pathways, programs, and individual genes. 
  - *Crucial caveat:* We make it very clear in the UI that this is an inferred, image-derived signature, **not** measured RNA-seq counts.
  - This matrix output allows clinicians and researchers to immediately ingest the predicted molecular state into downstream statistical tools or databases."
