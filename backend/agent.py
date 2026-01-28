from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
from backend.services.validation import ValidationService

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationService()
        self.confidence_threshold = 0.7

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

        # Step B/C: Action based on intent
        if intent == "OFF_TOPIC" or confidence < self.confidence_threshold:
            # Exception Case: Low Confidence or explicitly Off-Topic
            response_data["intent"] = "OFF_TOPIC"
            response_data["type"] = "off_topic"
            response_data["answer"] = "해당 문의는 고객 지원 범위에 포함되지 않습니다. 기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
        
        elif intent == "TECH_SUPPORT":
            # Knowledge RAG
            answer = self.knowledge.search_knowledge(query)
            response_data["type"] = "tech_support"
            response_data["answer"] = "기술 지원 도와드리겠습니다."
            response_data["rag_info"] = answer
        
        elif intent == "BILLING":
            transaction_result = self.transaction.process_transaction(intent, entity=query)
            response_data["type"] = "billing"
            response_data["data"] = transaction_result
            response_data["answer"] = "청구 지원 도와드리겠습니다."

        elif intent == "ORDER":
            transaction_result = self.transaction.process_transaction(intent, entity=query)
            response_data["type"] = "order"
            response_data["data"] = transaction_result
            response_data["answer"] = "주문 관리 도와드리겠습니다."

        elif intent == "ACCOUNT_MGMT":
            # Knowledge RAG for account issues
            answer = self.knowledge.search_knowledge(query)
            transaction_result = self.transaction.process_transaction(intent, entity=query)
            response_data["type"] = "account_mgmt"
            response_data["data"] = transaction_result
            response_data["answer"] = "계정 관리 도와드리겠습니다."
            response_data["rag_info"] = answer
            
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
