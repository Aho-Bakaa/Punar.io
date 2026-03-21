import uuid
from datetime import datetime
from typing import Dict, List, Optional
from ..models.transaction import Transaction, Settlement, UserCard, AuditLog, TransactionStatus

class MockDatabase:
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}
        self.settlements: Dict[str, Settlement] = {}
        self.user_cards: Dict[str, UserCard] = {}
        self.audit_logs: List[AuditLog] = []
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize mock card data"""
        mock_cards = [
            UserCard(
                card_token="tok_hdfc_1234",
                last4="1234",
                bank="HDFC",
                eligible=True,
                limit=50000,
                cardholder_name="Rajesh Kumar"
            ),
            UserCard(
                card_token="tok_icici_5678",
                last4="5678",
                bank="ICICI",
                eligible=True,
                limit=75000,
                cardholder_name="Priya Sharma"
            ),
            UserCard(
                card_token="tok_sbi_9012",
                last4="9012",
                bank="SBI",
                eligible=True,
                limit=30000,
                cardholder_name="Amit Patel"
            ),
            UserCard(
                card_token="tok_axis_3456",
                last4="3456",
                bank="AXIS",
                eligible=False,
                limit=0,
                cardholder_name="Neha Gupta"
            ),
            UserCard(
                card_token="tok_kotak_7890",
                last4="7890",
                bank="KOTAK",
                eligible=True,
                limit=25000,
                cardholder_name="Vikram Singh"
            )
        ]
        
        for card in mock_cards:
            self.user_cards[card.card_token] = card
    
    def create_transaction(self, transaction_data: dict) -> Transaction:
        transaction_id = f"TXN_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}"
        bank_transaction_id = f"BANK_{transaction_data['bank']}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"
        
        transaction = Transaction(
            id=transaction_id,
            bank_transaction_id=bank_transaction_id,
            **transaction_data,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.transactions[transaction_id] = transaction
        self._add_audit_log("TRANSACTION_CREATED", transaction_id, {"transaction": transaction.model_dump()})
        
        return transaction
    
    def update_transaction(self, transaction_id: str, updates: dict) -> Optional[Transaction]:
        if transaction_id not in self.transactions:
            return None
        
        transaction = self.transactions[transaction_id]
        for key, value in updates.items():
            setattr(transaction, key, value)
        transaction.updated_at = datetime.utcnow()
        
        self.transactions[transaction_id] = transaction
        self._add_audit_log("TRANSACTION_UPDATED", transaction_id, {"updates": updates})
        
        return transaction
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        return self.transactions.get(transaction_id)
    
    def get_transaction_by_reference(self, reference_id: str) -> Optional[Transaction]:
        for transaction in self.transactions.values():
            if transaction.reference_id == reference_id:
                return transaction
        return None
    
    def get_all_transactions(self) -> List[Transaction]:
        return list(self.transactions.values())
    
    def delete_transaction(self, transaction_id: str) -> bool:
        if transaction_id in self.transactions:
            del self.transactions[transaction_id]
            self._add_audit_log("TRANSACTION_DELETED", transaction_id, {})
            return True
        return False
    
    def create_settlement(self, settlement_data: dict) -> Settlement:
        settlement_id = f"STL_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        settlement = Settlement(
            id=settlement_id,
            **settlement_data,
            settled_at=datetime.utcnow()
        )
        
        self.settlements[settlement_data['transaction_id']] = settlement
        self._add_audit_log("SETTLEMENT_CREATED", settlement_data['transaction_id'], {"settlement": settlement.model_dump()})
        
        return settlement
    
    def get_settlement(self, transaction_id: str) -> Optional[Settlement]:
        return self.settlements.get(transaction_id)
    
    def get_user_card(self, card_token: str) -> Optional[UserCard]:
        return self.user_cards.get(card_token)
    
    def get_supported_banks(self) -> List[dict]:
        banks = []
        seen = set()
        for card in self.user_cards.values():
            if card.bank not in seen:
                banks.append({
                    "code": card.bank,
                    "name": f"{card.bank} Bank",
                    "supported": card.eligible,
                    "reward_rate": 1.0 if card.eligible else 0
                })
                seen.add(card.bank)
        return banks
    
    def _add_audit_log(self, log_type: str, transaction_id: Optional[str], data: dict):
        audit_log = AuditLog(
            id=f"LOG_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}",
            type=log_type,
            transaction_id=transaction_id,
            data=data,
            timestamp=datetime.utcnow()
        )
        self.audit_logs.append(audit_log)
    
    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        return self.audit_logs[-limit:]

db = MockDatabase()