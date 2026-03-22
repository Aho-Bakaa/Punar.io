# 💳 Credit Card Reward System - Mock Bank API

A mock bank API that converts e-waste value into credit card reward points. Perfect for recycling platforms and hackathon projects.

## 🚀 Quick Start

### API Base URL

http://localhost:3001


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

## 🔧 How to Use

### 1. Check if API is Running

```bash
curl https://localhost:3001/health
