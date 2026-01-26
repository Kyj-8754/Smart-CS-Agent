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
        
        # Mock logic based on keywords
        if "cancel" in intent.lower() or "cancel" in entity.lower() if entity else False:
            action_type = "cancel_order"
        elif "change" in intent.lower() or "modify" in intent.lower():
            action_type = "modify_account"
        else:
            action_type = "general_transaction"

        # Construct the pending action object
        pending_action = {
            "transaction_id": f"TXN-{int(datetime.now().timestamp())}",
            "action_type": action_type,
            "target_entity": entity or "Unknown Order/Account",
            "current_value": "Existing State",
            "new_value": "Requested State",
            "status": "pending_approval",  # CRITICAL: Waits for user approval
            "timestamp": datetime.now().isoformat()
        }
        
        return pending_action

    def execute_transaction(self, transaction_id: str):
        """
        Called ONLY after user approval.
        """
        # Logic to commit change to DB
        return {"status": "success", "transaction_id": transaction_id, "message": "Transaction committed to DB."}
