"""
CS Agent 메인 로직
A(분류) → B/C(처리) → D(검증) 파이프라인

TODO: conversation_history 구현
- process_query에 conversation_history 파라미터 추가
- router에서 프론트엔드가 보낸 대화 히스토리 받아서 전달
- ValidationAgent에 전달하여 맥락 기반 검증
"""

from .services.classification import ClassificationService
from .services.knowledge import KnowledgeService
from .services.transaction import TransactionService
from .services.validation import ValidationAgent
from langchain_openai import ChatOpenAI
from . import settings

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationAgent()
        
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY
        )

    async def process_query(self, query: str, conversation_history: list = None):
        # Step A: Classification via ClassificationService
        classification = await self.classifier.classify_intent(query)
        intent = classification["intent"]
        confidence = classification.get("confidence", 0.0)
        
        response_data = {
            "query": query,
            "intent": intent,
            "classification_details": classification
        }

        # Step B/C: Action based on intent
        # Scenario 1: OFF_TOPIC or Low Confidence
        if intent == "OFF_TOPIC" or confidence < 0.5:
            response_data["type"] = "off_topic"
            response_data["message"] = (
                "해당 문의는 고객 지원 범위에 포함되지 않습니다.\n"
                "기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
            )
        
        elif intent == "TECH_SUPPORT":
            # Scenario 2: Technical Support
            # knowledge.search_knowledge returns a dict with 'answer', 'confidence', etc.
            knowledge_result = self.knowledge.search_knowledge(query)
            response_data["type"] = "tech_support"
            
            if isinstance(knowledge_result, dict):
                response_data["message"] = knowledge_result.get("answer", "기술 지원 도와드리겠습니다.")
                # Add metadata from knowledge result to response
                if "data" not in response_data:
                    response_data["data"] = {}
                response_data["data"].update(knowledge_result)
            else:
                response_data["message"] = knowledge_result or "기술 지원 도와드리겠습니다."
        
        elif intent == "BILLING":
            # Scenario 3: Billing
            response_data["type"] = "billing"
            response_data["message"] = "청구 지원 도와드리겠습니다."
            # 실제 트랜잭션 처리가 필요하다면 아래와 같이 호출 가능
            # transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001")
            # response_data["data"] = transaction_result
            
        elif intent == "ORDER":
            # Scenario 4: Order
            response_data["type"] = "order"
            response_data["message"] = "주문 관리 도와드리겠습니다."
            
        elif intent == "ACCOUNT_MGMT":
            # Scenario 5: Account Management
            response_data["type"] = "account_mgmt"
            response_data["message"] = "계정 관리 도와드리겠습니다."
            
        else:
            response_data["type"] = "unknown"
            response_data["message"] = "죄송합니다. 요청하신 내용을 이해하지 못했습니다."

        # Step D: Validation (using ValidationAgent)
        validation = self.validator.validate_response(
            query=query,
            response=str(response_data.get("message", "")),
            conversation_history=conversation_history or [] 
        )
        
        if not validation["valid"]:
             response_data["message"] = validation["filtered_response"]
             response_data["blocked"] = True
             response_data["validation_issues"] = validation["issues"]

        return response_data
