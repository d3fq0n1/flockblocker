# /research

Academic papers, LPR vulnerability documentation, and Flock Safety architecture analysis.

## Scope

- Published academic work on ALPR (Automated License Plate Recognition) systems
- Flock Safety platform architecture: how reads flow from camera to database to query layer
- Documented vulnerabilities in OCR pipelines used by commercial LPR vendors
- Analysis of confidence thresholds and how "clean" reads are distinguished from failures
- Flock's data retention policies and inter-agency sharing topology

## Key Questions

- What OCR engine(s) does Flock use, and what are their known failure modes?
- How does the Flock backend deduplicate or validate incoming plate reads?
- What confidence score threshold causes a read to be stored vs. discarded?
- How are pattern-of-life queries constructed, and what data quality assumptions do they make?
