# Raspberry Pi 5 Hardware Catalog

Recommended hardware from CanaKit and Raspberry Pi Foundation for Public Accountability Station builds.

---

## Complete Kits (Recommended Starting Points)

### Tier 1: Full Desktop Stations

For fixed-installation PAS units with local display and storage.

| Product | Notes | Price |
|---------|-------|-------|
| CanaKit Raspberry Pi 5 Desktop PC with SSD and Monitor (Assembled) | Full station with monitor — use for public data terminals | — |
| CanaKit Raspberry Pi 5 Desktop PC with SSD (Assembled) | Headless station with SSD — primary recommended build | — |

### Tier 2: Starter Kits

For field-deployable or gimbal-mounted units.

| Product | Notes | Price |
|---------|-------|-------|
| CanaKit Raspberry Pi 5 Starter Kit - Turbine Black | Compact, good thermal management | — |
| CanaKit Raspberry Pi 5 Starter Kit - Aluminum | Best heat dissipation for outdoor enclosures | — |
| CanaKit Raspberry Pi 5 Starter Kit - Red/White | — | — |
| CanaKit Raspberry Pi 5 Starter MAX Kit - Turbine White | Extended kit, good baseline for PAS builds | — |

### Tier 3: AI-Capable Kits

For stations running on-device OCR and adversarial pattern testing.

| Product | Notes | Price |
|---------|-------|-------|
| CanaKit Raspberry Pi 5 8GB Dual Cooling GenAI Kit - 256GB Flash Edition (Assembled) | 256GB onboard, dual cooling — best for continuous OCR workloads | $389.95 |
| CanaKit Raspberry Pi 5 8GB Quick-Start AI Kit - 13/26 TOPS (Assembled) | Up to 26 TOPS with AI HAT — run adversarial models on-device | — |
| Raspberry Pi 5 Desktop Kit | Official kit, solid baseline | — |

---

## AI & ML Accelerators

For running the FlockBlocker adversarial testing suite and OCR engines on-device.

| Product | Notes | Price |
|---------|-------|-------|
| Raspberry Pi AI HAT+ 2 | Latest GenAI accelerator — preferred for new builds | — |
| Raspberry Pi AI HAT+ | First-gen AI accelerator | — |
| Raspberry Pi AI Kit for Pi 5 | Bundled AI acceleration package | — |

---

## Storage

Continuous capture and logging requires reliable, high-capacity storage.

| Product | Notes | Price |
|---------|-------|-------|
| Raspberry Pi Flash Drive - 128GB | USB flash — use for portable log transfer | — |
| Raspberry Pi SSD - 256 GB | Primary storage for fixed installations | — |
| CanaKit M.2 NVMe SSD | High-speed NVMe — pair with M.2 HAT+ | — |
| Raspberry Pi M.2 HAT+ | Required for NVMe SSD | — |
| Samsung EVO Plus MicroSD Card with Raspberry Pi OS | Boot media, pre-loaded OS | From $24.95 |

---

## Camera & Imaging

| Product | Notes | Price |
|---------|-------|-------|
| Raspberry Pi AI Camera | On-board neural network processing — preferred for PAS camera units | $75.95 |

---

## Enclosures & Thermal

Outdoor deployment demands proper thermal management.

| Product | Notes | Price |
|---------|-------|-------|
| CanaKit Turbine Case for Raspberry PI 5 - Black | — | $14.95 |
| CanaKit Turbine Case for Raspberry PI 5 - White | Matches PAS white palette | $14.95 |
| CanaKit Turbine Case for Raspberry PI 5 - Clear | Visible internals — institutional transparency aesthetic | $14.95 |
| CanaKit Aluminum Case for Raspberry Pi 5 | Best passive cooling for outdoor use | From $24.95 |
| Case for the Raspberry Pi 5 | Official case | From $10.95 |
| CanaKit Mega Heat Sink for Raspberry Pi 5 | — | $8.95 |
| CanaKit Fan for the Raspberry Pi 5 | Active cooling for enclosed deployments | $7.95 |
| CanaKit Heat Sinks for Raspberry Pi 5 (Set of 5) | Bulk thermal management | $6.95 |
| Raspberry Pi 5 Active Cooler | Official active cooler | $11.95 |

---

## Power

| Product | Notes | Price |
|---------|-------|-------|
| CanaKit USB-C PD PiSwitch for Raspberry Pi 5 | Remote power cycling — critical for unattended stations | $12.95 |
| CanaKit 5A USB-C Power Supply with PD for the Raspberry Pi 5 | — | $14.95 |
| Raspberry Pi 5 Power Supply (27W USB-C) | Official PSU | From $12.95 |
| RTC Battery for Raspberry Pi 5 | Maintains clock during power loss — important for timestamp integrity | $5.00 |

---

## Cables & Accessories

| Product | Notes | Price |
|---------|-------|-------|
| Raspberry Pi 5 Display Cable - 200mm | For public data terminal displays | $1.00 |
| Raspberry Pi 5 Camera Cable - 200mm | Camera module connection | $1.00 |
| Official Raspberry Pi Beginner's Guide - Pi 5 Edition | Reference | $24.95 |

---

## Bare Boards

For custom builds and bulk station deployments.

| Product | RAM | Price |
|---------|-----|-------|
| Raspberry Pi 5 1GB | 1GB | From $45.00 |
| Raspberry Pi 5 2GB | 2GB | From $65.00 |
| Raspberry Pi 5 4GB | 4GB — minimum for OCR workloads | From $85.00 |
| Raspberry Pi 5 8GB | 8GB — recommended for adversarial testing | From $125.00 |
| Raspberry Pi 5 16GB | 16GB — recommended for continuous multi-engine OCR | From $205.00 |

---

## Recommended Configurations

### Minimum Viable PAS (Documentation Only)

- Raspberry Pi 5 4GB
- Samsung EVO Plus MicroSD
- Raspberry Pi AI Camera
- CanaKit 5A USB-C Power Supply
- CanaKit Aluminum Case
- **~$200 total**

### Standard PAS (OCR + Documentation)

- Raspberry Pi 5 8GB
- Raspberry Pi SSD - 256GB + M.2 HAT+
- Raspberry Pi AI Camera
- Raspberry Pi AI HAT+
- CanaKit 5A USB-C Power Supply
- CanaKit USB-C PD PiSwitch
- RTC Battery
- CanaKit Aluminum Case
- **~$450 total**

### Full Station (Public Data Terminal)

- CanaKit Raspberry Pi 5 Desktop PC with SSD and Monitor (Assembled)
- Raspberry Pi AI HAT+ 2
- Raspberry Pi AI Camera
- CanaKit USB-C PD PiSwitch
- RTC Battery
- **~$600+ total**
