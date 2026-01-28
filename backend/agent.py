<<<<<<< HEAD
"""
CS Agent 메인 로직
A(분류) → B/C(처리) → D(검증) 파이프라인

TODO: conversation_history 구현
- process_query에 conversation_history 파라미터 추가
- router에서 프론트엔드가 보낸 대화 히스토리 받아서 전달
- ValidationAgent에 전달하여 맥락 기반 검증
"""

<<<<<<< HEAD
from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
<<<<<<< HEAD
from backend.services.validation import ValidationAgent
=======
from backend.services.validation import ValidationService
from langchain_openai import ChatOpenAI
>>>>>>> origin/kyj/transaction
<<<<<<< HEAD
=======
from services.classification import ClassificationService
from services.knowledge import KnowledgeService
from services.transaction import TransactionService
from services.validation import ValidationAgent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import settings
>>>>>>> origin/kyj/transaction
=======
import json
import os
from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
from backend.services.validation import ValidationService
>>>>>>> origin/feat/ohs-rag
=======
>>>>>>> origin/feat/ohs-rag

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
<<<<<<< HEAD
        self.validator = ValidationAgent()
        
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.0, # 분류를 위해 0으로 설정
            api_key=settings.OPENAI_API_KEY
        )

    async def process_query(self, query: str, conversation_history: list = None):
        # Step A: Classification via LLM
        intent = self._classify_intent_llm(query)
        
        classification = {"intent": intent} # 호환성을 위해 구조 유지
=======
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
>>>>>>> origin/feat/ohs-rag
        
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
<<<<<<< HEAD
        if intent == "tech_support":
            # Knowledge RAG
            answer = self.knowledge.search_knowledge(query)
            response_data["type"] = "tech_support"
            response_data["message"] = answer
        
        elif intent == "transaction":
            # Transaction Processing
            # Mock Logged-in User: user_001 (Kim Cheol-su)
            transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001") 
            response_data["type"] = "transaction"
            response_data["data"] = transaction_result
            response_data["message"] = transaction_result.get("message", "처리되었습니다.")
            
        elif intent == "chitchat":
            response_data["type"] = "chitchat"
            response_data["message"] = "안녕하세요! 무엇을 도와드릴까요?"
            
        else:
            response_data["type"] = "off_topic"
            response_data["message"] = "죄송합니다. 기술 지원이나 주문 관련 문의만 답변 드릴 수 있습니다."

        # Step D: Validation (using ValidationAgent)
        validation = self.validator.validate_response(
            query=query,
            response=str(response_data.get("message", "")),
            conversation_history=conversation_history or [] 
        )
        
        if not validation["valid"]:
             response_data["message"] = validation["filtered_response"]
=======
        if intent == "OFF_TOPIC" or confidence < self.confidence_threshold:
            # Exception Case: Low Confidence or explicitly Off-Topic
            response_data["intent"] = "OFF_TOPIC"
            response_data["type"] = "off_topic"
            response_data["answer"] = "해당 문의는 고객 지원 범위에 포함되지 않습니다. 기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
        
        elif intent == "TECH_SUPPORT":
            # Knowledge RAG (CSV)
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "tech_support"
<<<<<<< HEAD
=======
            response_data["answer"] = answer
        
        elif intent == "transaction":
            # Transaction Processing (returns pending approval)
            # Mock Logged-in User: user_001 (Kim Cheol-su)
            transaction_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001") 
            response_data["type"] = "transaction"
            response_data["data"] = transaction_result
            response_data["answer"] = transaction_result.get("message", "처리되었습니다.") # Use message from service
>>>>>>> origin/feat/ohs-rag
            
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
>>>>>>> origin/feat/ohs-rag
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
