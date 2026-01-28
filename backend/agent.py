"""
CS Agent 메인 로직 - 다이어그램 아키텍처 반영
1. Classification (분류 및 입력 검증)
2. Intent-based Processing (RAG 또는 DB 트랜잭션 수행)
3. Validation (최종 출력 검증 가드레일)
"""

from services.classification import ClassificationService
from services.knowledge import KnowledgeService
from services.transaction import TransactionService
from services.validation import ValidationAgent
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import settings

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationAgent()
        
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.5, # 생성적 답변을 위해 조정
            api_key=settings.OPENAI_API_KEY
        )

    async def process_query(self, query: str, conversation_history: list = None, session_id: str = "default_user"):
        # ---------------------------------------------------------
        # Step 1: 분류 에이전트 & 입력 검증 (Classification)
        # ---------------------------------------------------------
        classification = await self.classifier.classify_intent(query)
        intent = classification["intent"]
        confidence = classification.get("confidence", 0.0)
        
        response_data = {
            "query": query,
            "intent": intent,
            "classification_details": classification
        }

        # [다이어그램 로직] 주제 벗어남 판별
        if intent == "OFF_TOPIC" or confidence < 0.5:
            return {
                "message": "해당 문의는 지원 범위를 벗어납니다. 기술, 청구, 주문 문의를 도와드릴 수 있습니다.",
                "type": "off_topic",
                "intent": intent
            }

        # ---------------------------------------------------------
        # Step 2: 분류된 인텐트에 따른 처리 (Knowledge/Transaction)
        # ---------------------------------------------------------
        final_message = ""
        
        if intent == "TECH_SUPPORT":
        # B파트의 상세 검색 호출 (세션 ID 전달로 맥락 유지 활성화)
            knowledge_result = self.knowledge._search_knowledge_internal(
                query=query, 
             category="tech_support", 
                session_id=session_id
            )
        # B파트가 이미 LLM을 썼거나 캐시를 가져왔으므로 그 결과를 그대로 사용
            final_message = knowledge_result.get("answer", "")
            response_data["from_cache"] = knowledge_result.get("from_cache", False) # 캐시 여부 기록
            response_data["data"] = knowledge_result

        elif intent == "ORDER" or intent == "BILLING":
            # [다이어그램 로직] 주문 관리/청구 지원 에이전트 + 유저 계정 정보(Transaction)
            # TransactionService를 통해 DB 조회 로직 실행
            txn_result = self.transaction.process_transaction(intent, entity=query, user_id="user_001")
            # DB 조회 결과(상태값 등)를 바탕으로 LLM이 자연스러운 문장 생성
            final_message = await self._generate_llm_response(f"{intent} 담당", query, str(txn_result))
            response_data["data"] = txn_result

        elif intent == "ACCOUNT_MGMT":
            # [다이어그램 로직] 계정 관리 에이전트
            final_message = await self._generate_llm_response("계정 관리", query)

        response_data["message"] = final_message

        # ---------------------------------------------------------
        # Step 3: 출력 검증 필터 (Validation)
        # ---------------------------------------------------------
        validation = self.validator.validate_response(
            query=query,
            response=str(response_data.get("message", "")),
            conversation_history=conversation_history or [] 
        )
        
        # [다이어그램 로직] 부적절함 판별 시 메시지 차단
        if not validation["valid"]:
             response_data["message"] = "도움을 드릴 수 없습니다. (정책 위반 답변 차단)"
             response_data["blocked"] = True

        return response_data

    async def _generate_llm_response(self, role: str, query: str, context: str = ""):
        """분류된 에이전트 페르소나를 가지고 동적 답변 생성"""
        prompt = [
            SystemMessage(content=f"당신은 {role} 전문가입니다. 다음 컨텍스트를 참고하여 사용자에게 친절하고 구체적으로 답하세요: {context}"),
            HumanMessage(content=query)
        ]
        res = await self.llm.ainvoke(prompt)
        return res.content