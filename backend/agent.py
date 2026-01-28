import json
import os
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
            
            # Handle Ambiguity/Clarification
            if rag_result.get("needs_clarification"):
                response_data["answer"] = rag_result.get("clarification_question")
            else:
                response_data["answer"] = rag_result.get("answer") or "기술 지원 도와드리겠습니다."
            
            response_data["rag_info"] = rag_result
        
        elif intent == "BILLING":
            # 1. Knowledge RAG (CSV FAQ)
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "billing"
            
            # Handle Ambiguity/Clarification
            if rag_result.get("needs_clarification"):
                response_data["answer"] = rag_result.get("clarification_question")
            else:
                response_data["answer"] = rag_result.get("answer") or "청구 지원 도와드리겠습니다."
            
            response_data["rag_info"] = rag_result

            # 2. Stricter Action Trigger: Only for explicit requests
            action_keywords = ["신청", "해줘", "해주세오", "해달라", "결제하기", "납부하기", "입금"]
            if any(k in query for k in action_keywords):
                transaction_result = self.transaction.process_transaction(intent, entity=query)
                response_data["data"] = transaction_result

        elif intent == "ORDER":
            # 1. Knowledge RAG (CSV FAQ)
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "order"
            
            # Handle Ambiguity/Clarification
            if rag_result.get("needs_clarification"):
                response_data["answer"] = rag_result.get("clarification_question")
            else:
                response_data["answer"] = rag_result.get("answer") or "주문 관리 도와드리겠습니다."
                
            response_data["rag_info"] = rag_result

            # 2. Stricter Action Trigger
            action_keywords = ["취소", "변경", "수정", "반품", "환불", "조회해줘", "추적"]
            # Avoid triggering if it's a general complaint like "안 돼요"
            if any(k in query for k in action_keywords) and not ("안 돼" in query or "안되" in query):
                transaction_result = self.transaction.process_transaction(intent, entity=query)
                response_data["data"] = transaction_result

        elif intent == "ACCOUNT_MGMT":
            # 1. Check for personalized info lookup
            personalized_answer = None
            if "아이디" in query or "이름" in query:
                test_user = next((u for u in self.users_data if u['username'] == 'test'), None)
                if test_user:
                    if "아이디" in query:
                        personalized_answer = f"조회된 계정 정보입니다. 아이디는 '{test_user['username']}'입니다."
                    elif "이름" in query:
                        personalized_answer = f"조회된 계정 정보입니다. 이름은 '{test_user['name']}'입니다."

            # 2. Knowledge RAG (CSV FAQ)
            rag_result = self.knowledge.search_knowledge(query, category=category)
            response_data["type"] = "account_mgmt"
            
            # Handle Ambiguity/Clarification
            if personalized_answer:
                response_data["answer"] = personalized_answer
            elif rag_result.get("needs_clarification"):
                response_data["answer"] = rag_result.get("clarification_question")
            else:
                response_data["answer"] = rag_result.get("answer") or "계정 관리 도와드리겠습니다."
                
            response_data["rag_info"] = rag_result

            # 3. Stricter Action Trigger
            action_keywords = ["탈퇴", "삭제", "수정해줘", "초기화", "변경신청"]
            if any(k in query for k in action_keywords):
                transaction_result = self.transaction.process_transaction(intent, entity=query)
                response_data["data"] = transaction_result
            
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
