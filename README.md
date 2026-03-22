# 🟢 Punar.io: Blockchain-Enabled Circular E-Waste & Fintech Ecosystem

> **The Decentralized Bridge Between Consumer Waste, Local Businesses, and CPCB Compliance.**

---

## 📖 Project Overview

**punar.io** is a multi‑sided marketplace designed to solve the e‑waste crisis by incentivizing users to “disown” their old electronics. By integrating **Blockchain for provenance**, **AI for verification**, and a **Mock Banking API**, we turn environmental disposal into a rewarded financial transaction.

Our platform connects users with local technical shops for item verification, manages refurbishment commissions, and automates the **Extended Producer Responsibility (EPR)** data pipeline for government‑authorized recyclers and CPCB reporting.

# 🛠️ Technical Stack
The Eco-System Core
- **Frontend:** React Native for the interactive user interface.
- **Backend:** Node.js (Express) or Python (FastAPI) for marketplace orchestration.
- **Database:** MongoDB for transactional metadata.

## Trust & Automation Layer
- **Blockchain:** Polygon – Used to record the immutable lifecycle of the item (provenance).  
  Every item is minted as a unique Asset ID in the platform backend, and each major event is hashed and stored on‑chain.
- **AI/OCR:** PaddleOCR – Automatically extracts Brand, Model, and Purchase Date from purchase receipts to prevent fraud.
- **Fintech:** Mock Banking REST API – A custom‑built service to simulate Credit Card‑style reward‑point transactions in a sandboxed environment.

# 🚀 Key Features
1. **Rule‑Based Onboarding**  
   Smart Assessment: Users answer condition‑based questions that dynamically adjust based on the device type.  
   Proof of Purchase: OCR models verify the authenticity of the item using the receipt before it enters the bidding pool.

2. **Hyper‑Local Marketplace**  
   Geofenced Bidding: Nearby technical shops review the item’s digital health report and project a “Point Value.”  
   Logistics Choice: Users can choose between “Visit Shop” or “Home Pickup” for physical verification.

3. **Blockchain‑Backed EPR Compliance**  
   Immutable Event Log: Every major state change (SUBMITTED → INTAKE → TRIAGE → REFURBISHED / PARTS HARVESTED / RECYCLED) is hashed and stored on Polygon.  
   CPCB Transparency: Provides government‑authorized recyclers with a tamper‑evident data trail for EPR reporting.

4. **Dual‑Track Logic (with Parts Harvesting)**  
   - **Refurbish Track:** Shop repairs the item; device is listed and resold; platform takes a commission and logs CO₂ savings.  
   - **Parts‑Harvested Track:** Non‑functional devices with usable modules contribute spare parts to the marketplace.  
   - **Recycle Track:** Flagged‑for‑discard items are aggregated for bulk pickup; shops earn incentives as collection hubs.

# 🔄 System Workflow

<img width="1237" height="1051" alt="image" src="https://github.com/user-attachments/assets/ff788628-37e8-448f-93b9-a2e77fc37256" />

