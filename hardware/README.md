# /hardware

Raspberry Pi-based public accountability station hardware, catalog, and deployment specifications.

## Scope

- Raspberry Pi 5 hardware catalog and recommended configurations
- Public Accountability Station (PAS) design: gimbal-mounted, fixed-installation counter-surveillance platforms
- Bill of materials, assembly guides, and field deployment notes
- Station aesthetic and industrial design language

## Public Accountability Stations

Physical counter-surveillance installations designed for high-visibility deployment at or near Flock Safety camera locations. These are not covert. They are deliberately conspicuous — **obvious, bureaucratic, boringly threatening**.

### Design Language

Inspired by Federal Bureau of Control architecture. Think institutional yellow and clinical white. Brutalist geometry. The aesthetic of a government agency that has always existed and does not need to explain itself.

- **Primary palette:** Pantone 116 C (signal yellow), RAL 9003 (signal white)
- **Typography:** DIN 1451 or Eurostile Extended — mechanical, authoritative, unloved
- **Form factor:** Gimbal-mounted enclosure on pole or wall bracket. Visible from 100+ feet. No attempt to blend in.
- **Signage:** "PUBLIC ACCOUNTABILITY STATION" — no further explanation. A phone number or URL is optional. Ambiguity is the point.
- **Lighting:** Steady amber status LED. Not blinking. Not urgent. Just *on*.

The goal is not to look threatening in a way that provokes. The goal is to look like infrastructure that was always supposed to be there — the kind of thing you assume someone approved, mounted by someone whose job title you don't know, serving a purpose you can't quite identify but feel uncomfortable questioning.

### Station Functions

A deployed PAS can serve any combination of:

- **Flock camera documentation:** Continuously photograph and log the operational status of nearby LPR installations
- **OCR testing platform:** Run the FlockBlocker adversarial testing suite against live or simulated plate captures
- **Public data terminal:** Display FOIA-obtained Flock contract terms, cost data, and data retention policies for the municipality
- **Environmental logging:** Timestamp, weather, ambient IR levels — contextual data for adversarial pattern research
- **Mutual observation:** If they're watching the road, the road watches back

### Gimbal Mount

Pan-tilt gimbal with weatherproof housing. The gimbal exists partly for function (camera positioning) and partly for presence. A static camera is furniture. A camera on a gimbal is *watching*.

- 2-axis pan/tilt servo gimbal (180° pan, 90° tilt)
- Weatherproof IP65 enclosure, powder-coated yellow
- Pole-mount or wall-mount bracket (standard electrical conduit fitting)
- Internal Raspberry Pi 5 + camera module + SSD storage
- Solar panel option for off-grid deployment
- PoE HAT option for wired installations
