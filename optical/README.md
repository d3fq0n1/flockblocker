# /optical

Retroreflective and IR-based interference approaches.

## Scope

- Retroreflective material properties and their interaction with IR illuminators
- Near-infrared (NIR) LED arrays and their effect on CMOS sensors at LPR wavelengths (~850nm, ~940nm)
- Passive optical approaches: coatings, films, material science
- Analysis of Flock camera hardware: IR flash characteristics, sensor sensitivity curves
- The distinction between read-denial and read-corruption

## Position

Read-denial is the wrong objective. A failed capture is discarded by the pipeline and has zero downstream impact on the database. The system continues to function as designed.

The relevant question is whether optical methods can induce **consistent, confident misreads** — not whether they can degrade image quality. Degraded images are thrown away. Misreads are stored as ground truth.

This directory documents optical approaches evaluated through that lens.
