# 🟢 Punar.io: Blockchain-Enabled Circular E-Waste & Fintech Ecosystem

> **The Decentralized Bridge Between Consumer Waste, Local Businesses, and CPCB Compliance.**

---

## 📖 Project Overview

**punar.io** is a multi‑sided marketplace designed to solve the e‑waste crisis by incentivizing users to “disown” their old electronics. By integrating **Blockchain for provenance**, **AI for verification**, and a **Mock Banking API**, we turn environmental disposal into a rewarded financial transaction.

Our platform connects users with local technical shops for item verification, manages refurbishment commissions, and automates the **Extended Producer Responsibility (EPR)** data pipeline for government‑authorized recyclers and CPCB reporting.

---

```mermaid
flowchart TD
    U[User] -->|1. Uploads device details<br/>photos + bill/box (IMEI)| P[punar.io Platform]

    P -->|2. OCR parses bill<br/>(brand, model, date)| P
    P -->|Log hash: SUBMITTED| BC[Blockchain<br/>Event Log]

    P -->|3. Assign to nearest<br/>partner shop / pickup agent| S[Partner Technician]

    S -->|4. Physical intake<br/>IMEI match, weight, basic checks| P
    P -->|Log hash: INTAKE| BC

    S -->|5. Detailed manual triage<br/>(functionality + parts)| D{Technician decision}

    D -->|Fully functional<br/>(minor repair)| RF1[Fully Refurbished<br/>Device]
    D -->|Non-functional<br/>(but parts good)| RF2[Parts Harvested<br/>(Spare Modules)]
    D -->|End-of-life<br/>(no usable parts)| RC[Batch & Send<br/>to Recycler]

    RF1 -->|6a. Listed on marketplace<br/>as working device| M1[Marketplace Listing:<br/>Fully Functional]
    RF2 -->|6b. Parts listed on<br/>marketplace as spares| M2[Marketplace Listing:<br/>Spare Parts]
    RC  -->|6c. Processed by<br/>authorized recycler| R[Recycler]

    M1 -->|User rewarded<br/>ReCoins, CO₂ saved logged| OUT1[Impact Data<br/>(Refurb devices)]
    M2 -->|User rewarded<br/>ReCoins (lower), CO₂ saved logged| OUT2[Impact Data<br/>(Parts reuse)]
    R  -->|Weight + batch data<br/>for EPR & material recovery| OUT3[Impact Data<br/>(Recycling)]

    OUT1 -->|Aggregated reports<br/>& dashboards| OEM[OEM / Brand<br/>& Compliance Stakeholders]
    OUT2 --> OEM
    OUT3 --> OEM

    P -->|Log hash: TRIAGE| BC
    P -->|Log hash: REFURBISHED| BC
    P -->|Log hash: PARTS HARVESTED| BC
    P -->|Log hash: RECYCLED| BC
🛠️ Technical Stack
The Eco-System Core
Frontend: React Native for the interactive user interface.

Backend: Node.js (Express) or Python (FastAPI) for marketplace orchestration.

Database: MongoDB for transactional metadata.

Trust & Automation Layer
Blockchain: Polygon – Used to record the immutable lifecycle of the item (provenance).
Every item is minted as a unique Asset ID in the platform backend, and each major event is hashed and stored on‑chain.

AI/OCR: PaddleOCR – Automatically extracts Brand, Model, and Purchase Date from purchase receipts to prevent fraud.

Fintech: Mock Banking REST API – A custom‑built service to simulate Credit Card‑style reward‑point transactions in a sandboxed environment.

🚀 Key Features
1. Rule‑Based Onboarding
Smart Assessment: Users answer condition‑based questions that dynamically adjust based on the device type.

Proof of Purchase: OCR models verify the authenticity of the item using the receipt before it enters the bidding pool.

2. Hyper‑Local Marketplace
Geofenced Bidding: Nearby technical shops review the item’s digital health report and project a “Point Value.”

Logistics Choice: Users can choose between “Visit Shop” or “Home Pickup” for physical verification.

3. Blockchain‑Backed EPR Compliance
Immutable Event Log: Every major state change (SUBMITTED → INTAKE → TRIAGE → REFURBISHED / PARTS HARVESTED / RECYCLED) is hashed and stored on Polygon.

CPCB Transparency: Provides government‑authorized recyclers with a tamper‑evident data trail for EPR reporting.

4. Dual‑Track Logic (with Parts Harvesting)
Refurbish Track: Shop repairs the item; device is listed and resold; platform takes a commission and logs CO₂ savings.

Parts‑Harvested Track: Non‑functional devices with usable modules contribute spare parts to the marketplace.

Recycle Track: Flagged‑for‑discard items are aggregated for bulk pickup; shops earn incentives as collection hubs.

🔄 System Workflow
Onboarding:
User uploads item + receipt → OCR extracts metadata → Blockchain logs the SUBMITTED event.

Marketplace & Assignment:
Shops bid → User selects → Platform assigns technician.

Physical Verification & Triage:
Technician performs intake, then decides: Fully Functional, Parts‑Only, or Recycle.

Refurb / Parts / Recycle Path:

Refurbished / Parts‑Only: Platform lists item, collects commission, and credits user with ReCoins via Mock Bank API.

Recycled: Item added to “Bulk Collection” queue; status updated on‑chain as PARTS HARVESTED or RECYCLED.

Closing the Loop:
Recycler receives bulk batch → Updates status to Disposed → EPR data prepared from immutable ledger (hash‑checked, on‑chain‑linked).

🔒 Security & Integrity
Anti‑Gaming: OCR helps ensure users aren’t uploading random scrap for high‑value points.

Proof of Visit: Transactions are only finalized when the shop owner flags the verification, secured by a cross‑verification code between user and shop.

Data Integrity: By using Blockchain‑ logged event hashes, the compliance report sent to CPCB cannot be falsified by any party in the chain.

Blockchain is used only for integrity, not privacy:
No sensitive personal data lives on‑chain; only hashes of major events prove that the history cannot be silently rewritten.
