from datetime import datetime

class TransactionService:
    def __init__(self):
        # Mock Database
        self.orders = {
            "ORD-001": {"item": "Laptop", "status": "shipped"},
            "ORD-002": {"item": "Mouse", "status": "processing"}
        }

    def process_transaction(self, intent: str, entity: str = None) -> dict:
        """
        Processes transaction requests but returns them in a 'pending_approval' state.
        Real implementation would parse specific details from the query.
        """
        
        # Mock logic based on keywords or intent
        intent_lower = intent.upper()
        # Mapping technical action types to friendly labels
        action_mapping = {
            "BILLING": "청구/결제 지원",
            "ORDER": "주문/배송 관리",
            "ACCOUNT_MGMT": "계정/보안 관리",
            "cancel_order": "주문 취소 처리",
            "general_transaction": "일반 서비스 처리"
        }
        
        friendly_action = action_mapping.get(intent_lower, "서비스 지원")
        if entity and "cancel" in entity.lower():
            friendly_action = action_mapping["cancel_order"]

        # Construct the pending action object
        pending_action = {
            "transaction_id": f"TXN-{int(datetime.now().timestamp())}",
            "action_type": friendly_action,
            "target_entity": entity or "요청 항목",
            "current_value": "확인 중",
            "new_value": "처리 예정",
            "status": "pending_approval",
            "timestamp": datetime.now().isoformat()
        }
        
        return pending_action

    def execute_transaction(self, transaction_id: str):
        """
        Called ONLY after user approval.
        """
        # Logic to commit change to DB
        return {"status": "success", "transaction_id": transaction_id, "message": "요청하신 내역이 정상적으로 처리되었습니다. 이용해 주셔서 감사합니다."}
