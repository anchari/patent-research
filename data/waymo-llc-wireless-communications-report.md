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

---

## Appendix — Patent Reference

### Rotary Joint Communication

---

**[US9628170B2](https://patents.google.com/patent/US9628170B2/en) — Devices and Methods for a Rotary Joint with Multiple Wireless Links**
Issued 2017 · Daniel L. Rosenband, Pierre-Yves Droz, Min Wang, Etai Bruhis, Adam Brown, Samuel Lenius

Spinning sensor platforms (like lidar) on autonomous vehicles need continuous data links between the rotating and stationary parts of the vehicle, but physical cables would bind and wear. This invention establishes multiple simultaneous wireless links across the rotary joint gap, enabling bidirectional sensor data flow without slip rings. The multi-link design provides redundancy and higher aggregate bandwidth than a single wireless channel.

---

**[US10033456B2](https://patents.google.com/patent/US10033456B2/en) — Devices and Methods for a Rotary Joint with Multiple Wireless Links**
Issued 2018 · Daniel L. Rosenband, Pierre-Yves Droz, Min Wang, Etai Bruhis, Adam Brown, Samuel Lenius

Autonomous vehicle sensor platforms that rotate continuously require robust wireless data links across the rotation gap that can sustain data transfer through full 360-degree rotation. This continuation covers additional configurations of the multi-link rotary joint, including arrangements that maintain link quality as the relative angle between the two platforms changes. It ensures reliable communication between the spinning sensor head and the vehicle's processing systems under all operating conditions.

---

**[US10742315B2](https://patents.google.com/patent/US10742315B2/en) — Automotive Communication System with Dielectric Waveguide Cable and Wireless Contactless Rotary Joint**
Issued 2020 · Zhe Li, Min Wang, Michael Sleator

Spinning lidar platforms require both high-bandwidth data transfer and mechanical freedom to rotate continuously, but conventional wired connections can't span a rotating joint without wearing out. This invention combines a dielectric waveguide cable for high-speed signal propagation up to the joint with a wireless contactless rotary joint to cross the rotation gap, achieving both the bandwidth of a wired link and the durability of a non-contact interface.

---

**[US10862579B2](https://patents.google.com/patent/US10862579B2/en) — Devices and Methods for a Rotary Joint with Multiple Wireless Links**
Issued 2020 · Daniel L. Rosenband, Pierre-Yves Droz, Min Wang, Etai Bruhis, Adam Brown, Samuel Lenius

As autonomous vehicle lidar platforms grow in resolution and data rate, the wireless links across the rotary joint must scale accordingly. This continuation covers signal management and channel allocation across multiple simultaneous wireless links in the rotary joint, enabling the aggregate bandwidth to grow by adding parallel channels rather than requiring new hardware generations.

---

**[US10965367B2](https://patents.google.com/patent/US10965367B2/en) — Automotive Communication System with Dielectric Waveguide Cable and Wireless Contactless Rotary Joint**
Issued 2021 · Zhe Li, Min Wang, Michael Sleator

Reliable high-speed communication between the spinning sensor head and the vehicle body requires a rotary joint that handles both the physical rotation and the signal integrity demands of high-frequency data. This continuation extends the dielectric waveguide plus wireless rotary joint architecture to cover additional signal routing configurations and frequency bands, enabling the system to carry multiple independent data streams simultaneously through the same rotary joint.

---

**[US11804896B2](https://patents.google.com/patent/US11804896B2/en) — Automotive Communication System with Dielectric Waveguide Cable and Wireless Contactless Rotary Joint**
Issued 2023 · Zhe Li, Min Wang, Michael Sleator

As lidar sensors increase in channel count and resolution, the data throughput demands on the rotary joint grow substantially. This continuation covers the integration of the wireless joint with the vehicle's broader sensor data bus, including synchronization and arbitration of data streams from multiple sensors passing through the same rotary joint infrastructure.

---

**[US11841465B2](https://patents.google.com/patent/US11841465B2/en) — Wireless Power Transfer Via Rotary Link**
Issued 2023 · Joshua Jones, Gregory Hall, Alexander Zbrozek

The spinning lidar platform on an autonomous vehicle requires continuous electrical power, but wired connections through a rotating joint introduce wear and limit rotation speed. This invention delivers power wirelessly across the rotation gap using resonant inductive coupling through a transformer split across the two rotating platforms, regulated by an LLC resonant converter for high efficiency. Eliminating the electrical contacts removes a significant mechanical wear point from the lidar assembly.

---

**[US12228683B2](https://patents.google.com/patent/US12228683B2/en) — Wireless Power Transfer Via Rotary Link**
Issued 2025 · Joshua Jones, Gregory Hall, Alexander Zbrozek

Sustaining reliable wireless power delivery across a rotary joint under varying load conditions requires active control of the resonant converter to maintain efficiency as the lidar platform draws variable current. This continuation covers the dynamic power regulation aspects of the resonant inductive rotary power transfer system, including how the converter adapts its switching frequency to maintain high efficiency under changing load and alignment conditions.

---

**[US12416719B2](https://patents.google.com/patent/US12416719B2/en) — Waveguide Apparatus with High Speed Dual Channel Wireless Contactless Rotary Joint**
Issued 2025 · Zhe Li, Jamal Izadian, Pierre-Yves Droz, Min Wang, Samuel Lenius, Paul Karplus

Next-generation lidar sensors generate data volumes that exceed what single-channel wireless rotary joints can carry, requiring a new architecture to scale throughput without increasing the joint's physical size. This invention uses two parallel wireless channels through a bearing waveguide rotary joint, effectively doubling the available bandwidth across the rotation gap in the same physical footprint.

---

### Vehicle-to-Pedestrian (V2P) Communication

---

**[US10377374B2](https://patents.google.com/patent/US10377374B2/en) — Detection of Pedestrian Using Radio Devices**
Issued 2019 · Pierre-Yves Droz

Autonomous vehicles must reliably detect pedestrians even when they are occluded or in poor lighting conditions where cameras and lidar may struggle. This invention has the vehicle broadcast radio signals (Bluetooth, 802.11, or cellular) to solicit responses from radio-equipped devices carried by nearby people — such as smartphones — using signal response timing and strength to detect and locate pedestrians. The approach complements optical sensors by detecting pedestrians through obstructions and in zero-visibility conditions.

---

**[US10967856B2](https://patents.google.com/patent/US10967856B2/en) — Detection of Pedestrian Using Radio Devices**
Issued 2021 · Pierre-Yves Droz

Detecting pedestrians who carry radio-enabled devices (smartphones, wearables) provides a detection channel that is complementary to lidar and cameras — it works through walls, in darkness, and at range. This continuation covers additional radio protocols and signal processing approaches for the pedestrian detection system, including how the vehicle handles multiple simultaneous radio responses from a crowd to isolate individual pedestrians and estimate their positions.

---

**[US12122364B2](https://patents.google.com/patent/US12122364B2/en) — Detection of Pedestrian Using Radio Devices**
Issued 2024 · Pierre-Yves Droz

Radio-based pedestrian detection fills coverage gaps left by lidar and cameras — particularly at intersections, around corners, and in poor weather. This continuation covers the vehicle-side signal processing pipeline for parsing and localizing radio responses from pedestrian devices under real-world conditions including multipath propagation, varying device types, and dense crowds where many devices respond simultaneously.

---

### Charging Station Communication

---

**[US20260070457A1](https://patents.google.com/patent/US20260070457A1/en) — Antenna on Charger Infrastructure**
Published Application 2025 · Dieter Statezni, Sangram Patil

Autonomous vehicles accumulate terabytes of sensor data per day that must be offloaded for processing and model training, and scheduled charging sessions are the natural opportunity for bulk data transfer. This invention positions a high-throughput wireless antenna on the charging infrastructure adjacent to the vehicle's charging port, enabling simultaneous charging and high-speed sensor data offload through a predictable, close-range wireless link.

---

**[US12403790B2](https://patents.google.com/patent/US12403790B2/en) — Antenna on Charger Infrastructure**
Issued 2025 · Dieter Statezni, Sangram Patil

Offloading large sensor datasets from autonomous vehicles requires high-throughput wireless infrastructure at predictable locations where vehicles dwell for extended periods. This continuation covers the antenna design and signal management on the charger infrastructure side — including how the system handles multiple vehicles charging simultaneously, manages interference between adjacent charging bays, and authenticates vehicles before initiating the data transfer session.

---

### RF Spectrum Management

---

**[US20250166506A1](https://patents.google.com/patent/US20250166506A1/en) — Universal Spectrum Utilization Exchange for Radio Frequency Interference Mitigation and Avoidance**
Published Application 2023 · Michael Dane Fina, Filip Perich, Kenneth T. Ho

Autonomous vehicles and roadside infrastructure operating in dense urban environments cause and experience radio frequency interference from each other, but each device currently reacts to interference in isolation without sharing what it has observed. This invention creates a shared spectrum utilization exchange where vehicles and infrastructure report observed RFI parameters and locations to a central aggregator, which distributes interference maps back to all participants. The collective awareness lets the entire fleet proactively avoid known interference sources rather than each vehicle independently discovering and reacting to interference.

---

### Vehicle Cellular Connectivity

---

**[US9666937B2](https://patents.google.com/patent/US9666937B2/en) — LTE MIMO Antenna System for Automotive Carbon Fiber Rooftops**
Issued 2017 · Vijay Asrani, Felix Jose Alvarez Rivera, Douglas Blake Kough

Carbon fiber roofs used on autonomous vehicles for weight reduction are non-conductive and don't serve as a ground plane for antennas the way metal roofs do, degrading cellular performance. This invention designs an LTE MIMO antenna system for carbon fiber rooftops that uses the vehicle's metallic structural roof supports as antenna coupling elements rather than relying on a continuous ground plane.

---

### Asset & Fleet Tracking

---

**[US20230394257A1](https://patents.google.com/patent/US20230394257A1/en) — Wireless Anchors for Asset Tracking**
Published Application 2022 · David Andre, Erich Karl Nachbar

Tracking the physical location of vehicles and equipment in large garages and depots is difficult because GPS doesn't work indoors. This invention deploys fixed wireless anchor beacons at known locations that broadcast identification signals; reader devices measure received signal strength from multiple anchors and compute their position from the combined RSSI pattern. The approach enables fleet operators to track vehicles and equipment throughout large facilities without GPS or optical systems.
