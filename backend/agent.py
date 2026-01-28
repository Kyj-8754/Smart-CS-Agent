"""
CS Agent 메인 로직
A(분류) → B/C(처리) → D(검증) 파이프라인

TODO: conversation_history 구현
- process_query에 conversation_history 파라미터 추가
- router에서 프론트엔드가 보낸 대화 히스토리 받아서 전달
- ValidationAgent에 전달하여 맥락 기반 검증
"""

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
        self.validator = ValidationAgent()

    async def process_query(self, query: str):
        # Step A: Classification
        classification = await self.classifier.classify_intent(query)
        intent = classification.get("intent")
        
        response_data = {
            "query": query,
            "intent": intent,
            "classification_details": classification
        }

        # Step B/C: Action based on intent
        if intent == "tech_support":
            # Knowledge RAG
            answer = self.knowledge.search_knowledge(query)
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
            response_data["type"] = "off_topic"
            response_data["answer"] = "I can only assist with technical support or account transactions."

        # Step D: Validation
        # conversation_history: 프론트엔드가 보내는 사용자 대화 히스토리
        # 현재는 빈 배열 전달 중 → TODO에서 process_query 파라미터로 받아야 함
        validation = self.validator.validate_response(
            query=query,
            response=response_data.get("answer", ""),
            conversation_history=[]  # TODO: 실제 히스토리 전달 필요
        )
        if not validation["valid"]:
             response_data["answer"] = validation["filtered_response"]
             response_data["blocked"] = True
             response_data["validation_issues"] = validation["issues"]

        return response_data
