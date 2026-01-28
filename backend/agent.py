import json
import os
from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
<<<<<<< HEAD
from backend.services.validation import ValidationAgent
=======
from backend.services.validation import ValidationService
from langchain_openai import ChatOpenAI
>>>>>>> origin/kyj/transaction

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationService()
        self.confidence_threshold = 0.7
        self.users_data = self._load_users()

    def _load_users(self):
        try:
            path = "frontend/public/users.json"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f).get("users", [])
            return []
        except Exception:
            return []

    async def process_query(self, query: str):
        # Step A: Classification with RAG
        classification = await self.classifier.classify_intent(query)
        intent = classification.get("intent")
        confidence = classification.get("confidence", 0.0)
        
        response_data = {
            "query": query,
            "intent": intent,
            "classification_details": classification
        }

        # Mapping intents to knowledge categories
        intent_map = {
            "TECH_SUPPORT": "tech_support",
            "BILLING": "billing_support",
            "ORDER": "order_management",
            "ACCOUNT_MGMT": "account_management"
        }
        category = intent_map.get(intent)

        # Step B/C: Action based on intent
        if intent == "OFF_TOPIC" or confidence < self.confidence_threshold:
            # Exception Case: Low Confidence or explicitly Off-Topic
            response_data["intent"] = "OFF_TOPIC"
            response_data["type"] = "off_topic"
            response_data["answer"] = "해당 문의는 고객 지원 범위에 포함되지 않습니다. 기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
        
        elif intent == "TECH_SUPPORT":
            # Knowledge RAG (CSV)
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "tech_support"
            response_data["answer"] = answer
        
        elif intent == "transaction":
            # Transaction Processing (returns pending approval)
            # Mock Logged-in User: user_001 (Kim Cheol-su)
            transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001") 
            response_data["type"] = "transaction"
            response_data["data"] = transaction_result
            response_data["answer"] = transaction_result.get("message", "처리되었습니다.") # Use message from service
            
        elif intent == "chitchat":
            response_data["type"] = "chitchat"
            response_data["answer"] = "Hello! How can I help you today?"
            
        else:
            response_data["type"] = "fallback"
            response_data["answer"] = "도와드릴 다른 업무가 있을까요?"

        # Step D: Final Guardrail Validation (LLM-as-a-Judge)
        validation = self.validator.validate_output(response_data)
        if not validation["valid"]:
             response_data["answer"] = validation["safe_response"]
             response_data["blocked"] = True
             response_data["validation_issues"] = validation.get("issues", [])

        return response_data
