# /adversarial

Adversarial patch research for OCR and neural network misclassification.

## Scope

- Published adversarial example research targeting OCR systems
- Adversarial patches that induce character-level misclassification in plate recognition pipelines
- Physical-world adversarial examples robust to angle, lighting, and distance variation
- Transferability of adversarial perturbations across OCR architectures (CNN, CRNN, transformer)
- Targeted misclassification: inducing specific incorrect character reads, not random errors

## Key Literature

- Eykholt et al., "Robust Physical-World Attacks on Deep Learning Models" (CVPR 2018)
- Sharif et al., "Accessorize to a Crime" (CCS 2016)
- Brown et al., "Adversarial Patch" (NeurIPS 2017)
- Song et al., "Physical Adversarial Examples for Object Detectors" (USENIX 2018)
- Athalye et al., "Synthesizing Robust Adversarial Examples" (ICML 2018)

## Design Constraints

- Perturbations must survive printing at bumper-sticker scale
- Must remain effective across varying lighting, angles, and distances (10–50 ft typical Flock capture range)
- Must induce confident misreads, not low-confidence failures that get discarded
- Must not alter the plate itself or violate any plate display statute
- Must be visually unremarkable to human observers — a normal sticker, not an obvious countermeasure
