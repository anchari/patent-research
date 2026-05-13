# Waymo LLC — Wireless Communications Patent Portfolio
> Analysis based on 17 issued patents and published applications, 2017–2025

---

## 1. Where Waymo is innovating

### The spinning sensor problem is the central theme

More than half the portfolio — 9 of 17 patents — addresses a single engineering challenge unique to Waymo's sensor architecture: **how to move data and power across a continuously rotating joint**. Waymo's lidar units spin at high speed, meaning the sensor head and the vehicle body are always in relative motion. You can't run a cable through a rotating joint indefinitely without it winding up or wearing out. Waymo has invented around this constraint with three distinct approaches:

**Approach 1 — Multiple wireless links (2017–2020, Rosenband/Droz/Wang family):** The original solution establishes multiple parallel wireless channels across the rotation gap simultaneously. The multi-link design provides both redundancy and aggregate bandwidth that scales by adding channels rather than redesigning hardware. This family (US9628170, US10033456, US10862579) was filed early and forms the foundation of Waymo's rotary joint IP.

**Approach 2 — Dielectric waveguide + wireless hybrid (2020–2023, Li/Wang/Sleator family):** A more recent refinement runs a dielectric waveguide cable (high-speed, low-loss) up to the edge of the rotation gap, then crosses the gap wirelessly. This hybrid approach achieves better signal integrity than a purely wireless link for the non-rotating portion while retaining the contactless rotary crossing (US10742315, US10965367, US11804896). The latest patent in this trajectory (US12416719, 2025) upgrades to a dual-channel waveguide rotary joint, doubling throughput in the same footprint — consistent with the rising data volumes from higher-resolution next-generation lidar.

**Approach 3 — Wireless power transfer (2023–2025, Jones/Hall/Zbrozek family):** A parallel thread addresses power delivery to the spinning platform using resonant inductive coupling, eliminating the electrical slip rings that are a major source of mechanical wear in rotating systems (US11841465, US12228683). This complements the data link inventions — together they make the rotating sensor head fully wireless in both data and power.

The through-line across all three approaches is a progression from "can we do this wirelessly?" (2017) to "how do we scale throughput as sensors improve?" (2025). Waymo is clearly betting long-term on spinning lidar as its primary sensor modality and investing in a complete wireless infrastructure architecture to support it.

### Radio-based pedestrian detection (V2P)

Three patents (US10377374, US10967856, US12122364, all credited to Pierre-Yves Droz) cover a system where the autonomous vehicle actively transmits radio signals — Bluetooth, 802.11, or cellular — and detects pedestrians by listening for responses from their smartphones or wearables. This is notably different from passive sensing: rather than just observing RF emissions, the vehicle is soliciting responses to locate people who might not be visible to cameras or lidar.

The approach is strategically interesting because it exploits the near-universal smartphone penetration in pedestrian populations and works through physical obstructions. The three patents span 2019 to 2024, suggesting this is an active and maturing area rather than an exploratory one-off.

### Data offload at the charger

Two recent patents (US20260070457A1, US12403790B2, both 2025) describe a wireless antenna co-located with the vehicle's charging port on the charging infrastructure, enabling high-throughput sensor data upload during charging sessions. Waymo vehicles generate enormous data volumes in operation — this infrastructure solves the offload problem by exploiting the predictable dwell time and close range of the charging stop. The fact that this is appearing in the patent record now, rather than earlier, aligns with Waymo's commercial robotaxi scale-up: you only need this infrastructure once your fleet is large enough that terabytes per vehicle per day becomes a logistics problem.

### Fleet-level RF coordination (emerging)

One published application (US20250166506A1, 2023, still pending) describes a "Universal Spectrum Utilization Exchange" — a shared database where vehicles and roadside infrastructure report observed RF interference, and the aggregator distributes interference maps back across the fleet. This is a collective intelligence approach to spectrum management: instead of each vehicle independently discovering and reacting to interference, the whole fleet benefits from what any individual vehicle has observed. This is early-stage (published but not yet issued), but it points toward a fleet-coordination layer for RF that has no commercial equivalent today.

---

## 2. Where Waymo is not innovating — and why

### Cellular/5G/LTE connectivity
Waymo has exactly one patent touching cellular connectivity (US9666937 — an LTE MIMO antenna for carbon fiber roofs, 2017), and it addresses a mechanical integration problem rather than any protocol or systems innovation. There are no patents on 5G, C-V2X (cellular vehicle-to-everything), NR-V2X, or any aspect of cellular network integration.

This is almost certainly intentional. Qualcomm supplies the cellular modems and chipsets for Waymo's vehicles (as it does for most of the automotive industry), and the 3GPP standards bodies define the protocols. There is nothing proprietary to invent at the cellular layer — it's a commodity input. Waymo's engineering attention is on the problems where they can't buy a solution.

### V2X and DSRC
Zero patents on dedicated short-range communications (DSRC / 802.11p) or C-V2X vehicle-to-infrastructure protocols, despite these being the centerpiece of the automotive industry's cooperative driving agenda for over a decade. Waymo has consistently argued that their AV stack should work without any changes to infrastructure — a "camera, lidar, and radar only" philosophy that renders V2X irrelevant to their near-term operations. They may also be skeptical of V2X given its slow deployment history.

### WiFi / fleet mesh networking
No patents on wireless mesh networks, fleet-to-fleet communication, or WiFi-based telemetry despite these being obvious tools for a robotaxi operator. Cloud connectivity for operational telemetry appears to be handled via standard cellular, with no apparent proprietary wireless networking layer.

### Satellite connectivity
No patents on satellite connectivity (Starlink, Iridium, etc.) for remote or connectivity-degraded operation. Given that Waymo's current deployments are in dense urban areas with strong cellular coverage, satellite backup is probably not a priority.

### GPS / positioning
No positioning or GPS patents in this set. Waymo relies on Trimble, u-blox, and other GNSS suppliers for positioning hardware, combining it with their own HD map and sensor fusion — the wireless receiving side is purchased, the intelligence is proprietary.

---

## 3. Key inventors and their areas of specialization

### Pierre-Yves Droz — Sensor architecture and V2P ([LinkedIn](https://www.linkedin.com/in/pierre-yves-droz-5b06062/))
Droz appears on 4 patents across two distinct areas: the original multi-link wireless rotary joint family (as a co-inventor with Rosenband et al.) and all three V2P pedestrian radio detection patents (as sole inventor). His presence on both the foundational sensor platform work and the V2P line, combined with his sole-inventor status on the V2P patents, marks him as one of the broadest technical contributors in this portfolio. He is also a listed inventor on the latest dual-channel rotary joint patent (US12416719, 2025), suggesting he remains active at the frontier of the sensor communication problem.

*Droz co-founded 510 Systems, a robotics and computer vision company that Google acquired in 2011 as part of the early self-driving car effort — making him one of the longest-tenured people in the autonomous vehicle space.*

### Min Wang — Rotary joint communication architecture
Wang appears on 5 patents spanning both the original wireless link family (2017–2020) and the newer dielectric waveguide hybrid family (2020–2023), plus the 2025 dual-channel high-speed rotary joint. That cross-family presence across eight years makes Wang the most consistent contributor to the rotary joint data communication thread. The fact that Wang is on both the Rosenband-originated and the Li-originated sub-families suggests a systems-level architectural role bridging both approaches.

*No LinkedIn profile identified (name too common to confirm a match without additional signal).*

### Zhe Li — Advanced rotary joint systems
Li leads the dielectric waveguide plus wireless rotary joint family (US10742315, US10965367, US11804896) and is named on the 2025 dual-channel patent. His work represents the more recent, higher-performance generation of the rotary joint communication stack, where signal integrity over the full path — not just the wireless gap — becomes the binding constraint.

*No LinkedIn profile identified with confidence.*

### Daniel L. Rosenband — Original wireless rotary joint ([LinkedIn](https://www.linkedin.com/in/daniel-rosenband-4296266/))
Rosenband is lead inventor on the original three-patent "multiple wireless links" family (US9628170, US10033456, US10862579). His work established the conceptual foundation — that you solve the rotary joint problem with redundant wireless channels rather than a single high-reliability link — which subsequent inventors have refined and extended.

*Rosenband joined Waymo in 2013 and currently leads compute systems, silicon, and performance optimization. Before Waymo he founded Sandburst, a high-speed networking silicon startup acquired by Broadcom, and holds a BS from MIT — a hardware systems background that tracks well with the rotary joint communication architecture work.*

### Joshua Jones, Gregory Hall, Alexander Zbrozek — Wireless power for rotating platforms
This team holds both wireless power transfer via rotary link patents (US11841465, US12228683). Their work is the power-delivery counterpart to the data-link work of the Rosenband and Li families — together solving both halves of making the spinning sensor platform fully contact-free.

*Alexander Zbrozek ([LinkedIn](https://www.linkedin.com/in/sasha-zbrozek-84aa5aa/)) — known as Sasha — was a Staff Hardware Engineer at Waymo from 2011 to 2021, specializing in lidar hardware architecture, inertial navigation, precision timing, and power handling; he is now VP of Hardware at Saildrone. His decade-long tenure and focus on power systems makes him the natural lead for the wireless power work in this family. No LinkedIn profiles identified for Joshua Jones or Gregory Hall with sufficient confidence.*

### Dieter Statezni and Sangram Patil — Charging infrastructure communication
Statezni and Patil are the inventors on both charging station antenna patents (US20260070457A1, US12403790B2). This is a specialized infrastructure-side problem — how to build the depot communication system — that is distinct from the on-vehicle work and appears to represent a dedicated sub-team focused on fleet operations infrastructure.

*Sangram Patil ([LinkedIn](https://www.linkedin.com/in/sangram-patil-277a5522/)) has held roles at Waymo, Apple, and Tesla, consistent with a hardware engineering background in automotive and consumer electronics. No LinkedIn profile identified for Dieter Statezni.*

### Michael Dane Fina, Filip Perich, Kenneth T. Ho — RF spectrum management
This trio is named on the spectrum utilization exchange patent (US20250166506A1). Their work is the most network/systems-oriented in the portfolio, touching fleet coordination rather than individual vehicle hardware.

*Filip Perich ([LinkedIn](https://www.linkedin.com/in/filipperich), [personal site](https://perich.net)) holds a PhD and at Waymo leads software for next-generation automotive radar systems. His academic and publication record is in dynamic spectrum access, cognitive radio, and distributed pervasive systems — precisely the background needed to design a fleet-wide RF interference exchange. This is a clear deliberate hire rather than an internal career transition. No LinkedIn profiles identified for Michael Dane Fina or Kenneth T. Ho with sufficient confidence.*

---

## Summary

Waymo's wireless communications patent portfolio is narrow but deep. Rather than staking out broad platform positions in cellular, V2X, or general wireless networking, they have concentrated their inventive effort on two problems that are genuinely specific to their sensor and operations architecture: making the spinning lidar platform communicate reliably without physical contacts, and offloading the fleet's massive data volumes efficiently. The V2P radio detection work is the one area where they are developing genuinely new capabilities at the intersection of wireless and autonomy. Everything else — cellular, GPS, V2X, WiFi — they buy from the ecosystem. This is a disciplined portfolio that reflects a company with a clear theory of where their engineering differentiates them.
