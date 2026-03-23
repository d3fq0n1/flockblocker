# FlockBlocker

Data-layer countermeasures against Flock Safety license plate reader surveillance networks.

---

## The Problem

Flock Safety is not a camera company. It is a **centralized data aggregation platform** that sells municipalities a turnkey surveillance network and retains query access to every plate read collected across its entire customer base.

What this means in practice:

- **A private company operates the largest LPR database in the United States**, with reads from thousands of municipal deployments feeding a single queryable backend.
- **ICE and federal agencies access Flock data** through partnerships and subpoenas, turning local municipal camera purchases into federal immigration surveillance infrastructure.
- **A Texas sheriff searched the Flock database for vehicles that traveled from out of state to an abortion clinic.** This is not hypothetical — this is documented use of the system as deployed.
- **Wisconsin alone has 221 agencies querying Flock data**, meaning a plate read in Mauston is queryable by every participating department in the state and potentially nationwide through Flock's inter-network sharing.
- **There is no meaningful opt-out.** If you drive on a road with a Flock camera, your movements are logged, timestamped, and retained. You were not consulted.

Flock cameras are not solving crimes. They are building a **pattern-of-life database** — where you go, when, how often, and who you're near — operated by a private company, sold to the highest bidder, and accountable to no one.

## The Approach

Most anti-surveillance projects target the **optical layer**: obscure the plate, blind the camera, block the IR flash. These approaches fail for a simple reason — **a failed read is not a read**. The camera discards it. Nothing enters the database. The surveillance system is unaffected.

FlockBlocker targets the **data layer**.

The goal is to induce **confident misreads** — plate captures that the OCR pipeline processes with high confidence and stores as clean data. These false reads enter the Flock database as ground truth. Over time, they:

- **Corrupt pattern-of-life analysis** by injecting false movement records
- **Degrade the reliability of alert-based queries** by increasing false positive rates
- **Undermine prosecutorial use** of Flock data by introducing reasonable doubt about data integrity
- **Erode institutional trust** in the platform as a reliable intelligence source

A camera that can't read a plate is an inconvenience. A database full of confident garbage is a **liability**.

This approach builds on published academic research in adversarial machine learning, specifically physical-world adversarial examples that cause neural network misclassification in vision systems.

## Directory Structure

```
/research        Academic papers, LPR vulnerability docs, Flock architecture analysis
/optical         Retroreflective and IR-based interference approaches
/adversarial     Adversarial patch research for OCR/neural net misclassification
/legal           FOIA templates, open records requests, municipal contract analysis
/distribution    Bumper sticker designs, organic spread strategy, print specs
/hardware        Raspberry Pi hardware catalog, public accountability station specs
/tools           Working code and scripts
```

## Legal Notice

This project operates entirely within legal boundaries.

- All adversarial techniques reference **published academic research** in adversarial machine learning (CVPR, NeurIPS, USENIX, CCS).
- No component of this project involves **physically altering, obscuring, or obstructing** a license plate.
- No instructions are provided for violating **any state or federal plate display statute**.
- Adversarial visual patterns placed on legal vehicle accessories (bumper stickers, frames) that affect machine perception but remain visually unremarkable to human observers occupy a legal space that **no current statute addresses**.
- The FOIA and legal research components of this project exercise **constitutionally protected rights** to government transparency and public records access.

If you believe automated mass surveillance should be immune to public scrutiny and countermeasure research, we disagree.

## Contributing

This project is open to collaboration, particularly from:

- Residents of Flock-contracted municipalities who want to understand what their city purchased
- Adversarial ML researchers interested in physical-world transferability
- Attorneys and legal researchers working on surveillance technology law
- Anyone who has filed FOIA requests for Flock Safety contracts and wants to share findings

Open an issue or submit a PR. If you're in a Flock-contracted municipality, note which one — local knowledge matters.

## Background

On **March 19, 2026**, a formal decommission notice was sent to the **City of Mauston, Wisconsin** requesting the removal of Flock Safety LPR cameras from municipal infrastructure. This project exists because the request alone is not enough. The surveillance apparatus will not dismantle itself.

---

*"The clock is running."*
