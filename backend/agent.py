"""
CS Agent 메인 로직
A(분류) → B/C(처리) → D(검증) 파이프라인

TODO: conversation_history 구현
- process_query에 conversation_history 파라미터 추가
- router에서 프론트엔드가 보낸 대화 히스토리 받아서 전달
- ValidationAgent에 전달하여 맥락 기반 검증
"""

import os
from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
from backend.services.validation import ValidationService
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
try:
    from backend import settings
except ImportError:
    class settings:
        MODEL_NAME = "gpt-4o"
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationService()
        self.confidence_threshold = 0.7

    async def process_query(self, query: str, conversation_history: list = None):
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
            "ACCOUNT_MGMT": "account_management",
            "transaction": "order_management" # compatibility
        }
        category = intent_map.get(intent)

        # Step B/C: Action based on intent
        if intent == "OFF_TOPIC" or confidence < self.confidence_threshold:
            response_data["type"] = "off_topic"
            response_data["answer"] = "해당 문의는 고객 지원 범위에 포함되지 않습니다. 기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
        
        elif intent == "TECH_SUPPORT":
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "tech_support"
            response_data["answer"] = rag_result.get("answer") or "기술 지원 도와드리겠습니다."
            response_data["rag_info"] = rag_result
        
        elif intent == "BILLING" or intent == "transaction": # Map transaction to BILLING if it looks like refund
            if "환불" in query or "결제" in query:
                rag_result = self.knowledge.search_knowledge(query, category="billing_support")
                response_data["type"] = "billing"
                response_data["answer"] = rag_result.get("answer")
                
                # Action Trigger
                action_keywords = ["신청", "해줘", "해주세오", "해달라"]
                if any(k in query for k in action_keywords):
                    transaction_result = self.transaction.process_transaction("BILLING", entity=query, user_id="user_001")
                    response_data["data"] = transaction_result
                    if transaction_result.get("message"):
                        response_data["answer"] = transaction_result["message"]
            else:
                # Other transactions
                transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001")
                response_data["type"] = "transaction"
                response_data["data"] = transaction_result
                response_data["answer"] = transaction_result.get("message", "처리되었습니다.")

        elif intent == "ORDER":
            rag_result = self.knowledge.search_knowledge(query, category="order_management")
            response_data["type"] = "order"
            response_data["answer"] = rag_result.get("answer")
            
            action_keywords = ["취소", "변경", "수정", "반품"]
            if any(k in query for k in action_keywords):
                transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001")
                response_data["data"] = transaction_result
                if transaction_result.get("message"):
                    response_data["answer"] = transaction_result["message"]

        elif intent == "chitchat":
            response_data["type"] = "chitchat"
            response_data["answer"] = "안녕하세요! 무엇을 도와드릴까요?"
            
        else:
            response_data["type"] = "off_topic"
            response_data["answer"] = "죄송합니다. 기술 지원이나 주문 관련 문의만 답변 드릴 수 있습니다."

        # Compatibility for message/answer
        response_data["message"] = response_data.get("answer")

        # Step D: Final Guardrail Validation
        validation = self.validator.validate_output(response_data)
        if not validation["valid"]:
             response_data["answer"] = validation["safe_response"]
             response_data["message"] = validation["safe_response"]
             response_data["blocked"] = True
             response_data["validation_issues"] = validation.get("issues", [])

        return response_data

    def _classify_intent_llm(self, query: str) -> str:
        """LLM을 사용하여 사용자 의도를 분류합니다."""
        try:
            prompt = ChatPromptTemplate.from_template(
                """
                Classify the following user query into one of these intents:
                - transaction: Order status, cancellation, shipping, refund, account changes.
                - tech_support: Technical issues, login problems, errors, how-to guides.
                - chitchat: Greetings, small talk, pleasantries.
                - off_topic: Anything else not related to the above.
                
                Return ONLY the intent name (lowercase).
                
                Query: {query}
                Intent:
                """
            )
            chain = prompt | self.llm
            result = chain.invoke({"query": query})
            intent = result.content.strip().lower()
            
            valid_intents = ["transaction", "tech_support", "chitchat", "off_topic"]
            if intent not in valid_intents:
                return "off_topic"
            return intent
            
        except Exception as e:
            print(f"LLM Classification Error: {e}")
            # Fallback to existing regex classifier if LLM fails
            # (Synchronous call wrapper for async method is tricky here, so simple fallback)
            return "transaction" if "주문" in query or "배송" in query else "off_topic"
