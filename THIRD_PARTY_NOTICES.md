# Third-party software and data notices

NeuroBridge's [MIT license](LICENSE) covers **original repository code only**. It does not relicense third-party source, model weights, data, or images.

## Encoders and dependencies

- **CTransPath / TransPath**, Wang et al., *Medical Image Analysis* (2022). Upstream code and weights: [TransPath](https://github.com/Xiyue-Wang/TransPath). Check the upstream source and weight terms before download, reuse, or redistribution. No third-party pretrained weights are shipped here.
- **ResNet-50**, He et al. (2016); pretrained model resources retain their provider's terms.
- **PyTorch**, **torchvision**, **scikit-learn**, **NumPy**, **SciPy**, **pandas**, **OpenSlide**, and other dependencies are maintained by their respective authors. Their terms are provided by the upstream projects.

Do not presume that code availability grants permission to redistribute trained model weights.

## Biomedical datasets

TCGA-GBM and TCGA-LGG are provided through the [NCI Genomic Data Commons](https://portal.gdc.cancer.gov/). CPTAC-GBM imaging is obtained from the [Cancer Imaging Archive](https://www.cancerimagingarchive.net/collection/cptac-gbm/). These remain under their respective access terms and usage policies.

**No diagnostic WSIs, sequencing archives, private clinical records, or patient-identifiable source data are redistributed with this repository.** When obtaining data, review access and redistribution terms at the source.

For scientific and data provenance requirements, see [the research guide](docs/REPRODUCIBILITY.md).
