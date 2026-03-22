# 🟢 Punar.io: Blockchain-Enabled Circular E-Waste & Fintech Ecosystem

> **The Decentralized Bridge Between Consumer Waste, Local Businesses, and CPCB Compliance.**

---

## 📖 Project Overview
**punar.io** is a multi-sided marketplace designed to solve the e-waste crisis by incentivizing users to "disown" their old electronics. By integrating **Blockchain for provenance**, **AI for verification**, and a **Mock Banking API**, we turn environmental disposal into a rewarded financial transaction. 

Our platform connects users with local technical shops for item verification, manages refurbishment commissions, and automates the **Extended Producer Responsibility (EPR)** data pipeline for government-authorized recyclers and CPCB reporting.

---

```mermaid
---
config:
  layout: elk
---
flowchart TD
    U[User] -->|1. Uploads device details<br/>photos + bill/box IMEI| P[punar.io Platform]

    P -->|2. OCR parses bill<br/>brand, model, date| P
    P -->|Log hash: SUBMITTED| BC[Blockchain<br/>Event Log]

    P -->|3. Assign to nearest<br/>partner shop / pickup agent| S[Partner Technician]

    S -->|4. Physical intake<br/>IMEI match, weight, basic checks| P
    P -->|Log hash: INTAKE| BC

    S -->|5. Detailed manual triage<br/>functionality + parts| D{Technician decision}
    D -->|Fully functional<br/>minor repair| RF1[Fully Refurbished<br/>Device]
    D -->|Non-functional<br/>but parts good| RF2[Parts Harvested<br/>Spare Modules]
    D -->|End-of-life<br/>no usable parts| RC[Batch & Send<br/>to Recycler]

    RF1 -->|6a. Listed on marketplace<br/>as working device| M1[Marketplace Listing:<br/>Fully Functional]
    RF2 -->|6b. Parts listed on<br/>marketplace as spares| M2[Marketplace Listing:<br/>Spare Parts]
    RC  -->|6c. Processed by<br/>authorized recycler| R[Recycler]

    M1 -->|User rewarded<br/>ReCoins, CO₂ saved logged| OUT1[Impact Data<br/>Refurb devices]
    M2 -->|User rewarded<br/>ReCoins lower, CO₂ saved logged| OUT2[Impact Data<br/>Parts reuse]
    R  -->|Weight + batch data<br/>for EPR & material recovery| OUT3[Impact Data<br/>Recycling]

    OUT1 -->|Aggregated reports<br/>& dashboards| OEM[OEM / Brand<br/>& Compliance Stakeholders]
    OUT2 --> OEM
    OUT3 --> OEM
    P -->|Log hash: TRIAGE| BC
    P -->|Log hash: REFURBISHED| BC
    P -->|Log hash: PARTS HARVESTED| BC
    P -->|Log hash: RECYCLED| BC

    class BC fill:#ede7f6,stroke:#5e35b1,color:#311b92,stroke-width:1.5px


## 🛠️ Technical Stack

### **The Eco-System Core**
* **Frontend:** `React Native` for the interactive user interface.
* **Backend:** `Node.js (Express)` or `Python (FastAPI)` for marketplace orchestration.
* **Database:** `MongoDB` for transactional metadata.
  
### **Trust & Automation Layer**
* **Blockchain:** `Polygon` – Used to record the immutable lifecycle of the item (Provenance). Every item is minted as a unique Asset ID.
* **AI/OCR:** `paddle` – Automatically extracts Brand, Model, and Date from purchase receipts to prevent fraud.
* **Fintech:** `Mock Banking REST API` – A custom-built service to simulate Credit Card reward point transactions in a sandboxed environment.

---

## 🚀 Key Features

### 1. Rule-Based Onboarding
* **Smart Assessment:** Users answer condition-based questions that dynamically adjust based on the device type.
* **Proof of Purchase:** OCR models verify the authenticity of the item using the receipt before it enters the bidding pool.

### 2. Hyper-Local Marketplace
* **Geofenced Bidding:** Nearby technical shops review the item's digital health report and project a "Point Value."
* **Logistics Choice:** Users can choose between "Visit Shop" or "Home Pickup" for physical verification.

### 3. Blockchain-Backed EPR Compliance
* **Immutable Ledger:** Every state change (User ➔ Shop ➔ Recycler) is an on-chain transaction.
* **CPCB Transparency:** Provides government-authorized recyclers with tamper-proof data to issue EPR certificates without manual audits.

### 4. Dual-Track Logic
* **Refurbish Track:** If a shop repairs the item, the platform collects a commission.
* **Recycle Track:** If flagged for discard, the platform aggregates items for bulk pickup. Shops receive incentives for acting as collection hubs.

---

## 🔄 System Workflow

1.  **Onboarding:** User uploads item + receipt ➔ **OCR** extracts metadata ➔ **Blockchain** creates the asset record.
2.  **Marketplace:** Shops bid ➔ User selects ➔ Physical Verification occurs via OTP handshake.
3.  **The Fork:**
    * **Refurbish:** Platform takes commission ➔ **Mock Bank API** credits user points.
    * **Recycle:** Item added to "Bulk Collection" queue ➔ Status updated on-chain.
4.  **Closing the Loop:** Recycler receives bulk batch ➔ Updates status to *Disposed* ➔ **EPR Certificate** generated from immutable ledger data.

---

## 🔒 Security & Integrity
* **Anti-Gaming:** The OCR receipt check ensures users aren't uploading random scrap for high-value points.
* **Proof of Visit:** Transactions are only finalized when the shop owner flags the verification, secured by a cross-verification code between user and shop.
* **Data Integrity:** By using Blockchain, the compliance report sent to the CPCB cannot be falsified by any party in the chain.

---
