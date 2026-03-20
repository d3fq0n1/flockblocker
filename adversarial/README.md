# /adversarial

Adversarial patch research for OCR and neural network misclassification.

## Scope

- Published adversarial example research targeting OCR systems
- Adversarial patches that cause character-level misclassification in plate recognition
- Physical-world adversarial examples (robust to angle, lighting, distance variation)
- Transferability of adversarial perturbations across different OCR architectures
- Targeted misclassification: inducing reads of specific incorrect characters vs. random errors

## Key Literature

- Eykholt et al., "Robust Physical-World Attacks on Deep Learning Models" (CVPR 2018)
- Sharif et al., "Accessorize to a Crime" (CCS 2016)
- Brown et al., "Adversarial Patch" (NeurIPS 2017)
- Song et al., "Physical Adversarial Examples for Object Detectors" (USENIX 2018)

## Design Constraints

- Perturbations must survive printing at bumper-sticker scale
- Must be robust across varying lighting, angles, and distances (10–50 ft typical for Flock)
- Must induce confident misreads, not low-confidence failures
- Must not alter the plate itself or violate plate display statutes
