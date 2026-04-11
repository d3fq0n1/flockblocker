# /research

Academic papers, LPR vulnerability documentation, and Flock Safety architecture analysis.

## Scope

- Published academic work on ALPR (Automated License Plate Recognition) systems and their documented failure modes
- Flock Safety platform architecture: the path from camera to edge processing to cloud database to query layer
- Cataloged vulnerabilities in OCR pipelines used by commercial LPR vendors
- Confidence threshold analysis — the boundary between stored reads and discarded noise
- Flock's data retention policies, inter-agency sharing topology, and the absence of correction mechanisms

## Key Questions

- What OCR engine(s) does Flock use, and what are their known failure modes?
- How does the Flock backend deduplicate or validate incoming plate reads? (Current evidence: it does not validate against registration databases.)
- What confidence score threshold determines whether a read is stored or discarded?
- How are pattern-of-life queries constructed, and what data quality assumptions do they depend on?
- What is the actual false positive rate under adverse conditions, and how does it compare to Flock's published claims?

## Context

Flock Safety processes billions of plate reads across 40,000+ cameras serving 5,000+ law enforcement agencies. No independent adversarial robustness audit of their pipeline has been published. No vendor in this space publishes one. The research in this directory exists to fill that gap.
