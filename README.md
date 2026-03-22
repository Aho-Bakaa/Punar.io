# 💳 Credit Card Reward System - Mock Bank API

A mock bank API that converts e-waste value into credit card reward points. Perfect for recycling platforms and hackathon projects.

---

## 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **💰 Instant Points Conversion** | ₹1 = 10 points. A ₹500 device instantly becomes 5,000 reward points |
| **💳 Multi-Bank Support** | HDFC, ICICI, SBI with built-in card validation and test cards |
| **🔄 Idempotent Processing** | Unique reference IDs prevent duplicate points issuance |
| **📊 Transaction Tracking** | Full status history with unique transaction IDs |
| **🔌 Webhook Ready** | Settlement notifications with retry logic |
| **🛡️ Fraud Prevention** | Card validation, limits, duplicate checks, and risk scoring |
| **📖 Swagger UI** | Interactive API documentation |
| **🌐 CORS Enabled** | Ready for frontend integration |

---




## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if API is running |
| GET | `/` | Welcome message |
| POST | `/api/rewards/issue` | Issue reward points |
| GET | `/api/rewards/transaction/{id}` | Get transaction status |
| GET | `/api/rewards/banks` | List supported banks |
| GET | `/api/admin/dashboard` | System statistics |
| GET | `/api/admin/transactions` | All transactions |

---

## Install Dependencies

```bash
   pip install -r requirements.txt
```



## 🔧 How to Use

### 1. Check if API is Running

```bash
curl https://localhost:3001/health

