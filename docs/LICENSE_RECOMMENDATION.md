# Third-Party License Audit & License Recommendation

## 1. Third-Party Dependency Audit

| Component | Provider / Author | License Type | Distribution Permitted |
|---|---|---|---|
| Python Codebase | NeuroBridge / Hazrat Maghaz | MIT License | Yes |
| PyTorch, torchvision | PyTorch Foundation | BSD-style | Yes |
| CTransPath Architecture | Xiyue Wang et al. (TransPath) | GPL-3.0 | Yes (Source code reference) |
| CTransPath Pre-trained Weights | Xiyue Wang et al. | Research / Non-commercial | **No direct weight redistribution in git repo** |
| TCGA-GBM / TCGA-LGG Data | NCI GDC | Open Access / NIH Data Policy | External download only via GDC API |
| CPTAC-GBM Data | NCI PDC | Open Access / NIH Data Policy | External download only via PDC API |

---

## 2. License Recommendation
- **Recommended Codebase License**: **MIT License** (for all original Python source code, scripts, and documentation).
- **Model Weights & External Code Policy**:
  - Do **not** commit `ctranspath.pth` or third-party model weights directly into the Git repository.
  - Provide automated download scripts and configuration instructions pointing to the original official CTransPath repository (`models/external/TransPath`).
