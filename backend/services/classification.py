from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

class ClassificationResult(BaseModel):
    intent: str = Field(description="The classification intent: 'OFF_TOPIC', 'TECH_SUPPORT', 'BILLING', 'ORDER', or 'ACCOUNT_MGMT'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the classification using historical cases and keywords")

class ClassificationService:
    def __init__(self):
        # Using a placeholder model/API key for now. 
        # In production, ensure OPENAI_API_KEY is set in .env
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        
        # Initialize RAG for classification using historical cases
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            historical_cases = [
                Document(page_content="로그인 문제, 비밀번호 초기화, 아이디 찾기 관련 문의", metadata={"intent": "ACCOUNT_MGMT"}),
                Document(page_content="환불 요청, 결제 오류, 청구서 확인, 환불이 안 돼요", metadata={"intent": "BILLING"}),
                Document(page_content="전원이 안 켜짐, 오류 메시지, 설치 방법, 멈춤 현상", metadata={"intent": "TECH_SUPPORT"}),
                Document(page_content="주문 조회, 배송 상태, 주문 변경, 배송이 안 와요", metadata={"intent": "ORDER"}),
                Document(page_content="너 누구니?, 날씨 어때?, 욕설, 잡답", metadata={"intent": "OFF_TOPIC"})
            ]
            self.db = FAISS.from_documents(historical_cases, self.embeddings)
        except Exception as e:
            print(f"Classification RAG Init Error: {e}")
            self.db = None

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful customer service AI. Classify the user input into one of these categories: \n"
                        "- 'OFF_TOPIC': Questions unrelated to the service (e.g., 'Are you AI?', general chat, profanity).\n"
                        "- 'TECH_SUPPORT': Hardware/software technical issues (Keywords: 오류, 멈춤, 설치, 실행, 전원, 업데이트).\n"
                        "- 'BILLING': Payment, refunds, billing, fees, receipts. This includes issues like 'refund not working' (Keywords: 결제, 환불, 청구, 금액, 영수증, 납부).\n"
                        "- 'ORDER': Order lifecycle (status, delivery, shipping, cancellation, changes) (Keywords: 주문, 배송, 취소, 택배, 송장).\n"
                        "- 'ACCOUNT_MGMT': User identity (login, password, account info, ID, authentication) (Keywords: 로그인, 비밀번호, 계정, 아이디, 인증).\n\n"
                        "Reference historical cases: {historical_context}\n"
                        "CRITICAL: If a query contains financial terms like '환불' (refund) or '결제' (payment), it MUST be classified as 'BILLING' even if it mentions general issues like 'doesn't work' (안 돼요).\n"
                        "{format_instructions}"),
            ("user", "{query}")
        ]).partial(format_instructions=self.parser.get_format_instructions())

    def _get_rule_based_intent(self, query: str) -> str:
        """Simple keyword based intent as a backup/helper"""
        query = query.lower()
        if any(k in query for k in ["환불", "결제", "청구", "요금", "영수증", "금액"]):
            return "BILLING"
        if any(k in query for k in ["주문", "배송", "택배", "송장", "취소", "변경"]):
            # Note: "취소", "변경" can be billing too, but usually order in this context
            if "환불" in query or "결제" in query:
                return "BILLING"
            return "ORDER"
        if any(k in query for k in ["로그인", "비밀번호", "아이디", "계정", "인증", "탈퇴"]):
            return "ACCOUNT_MGMT"
        if any(k in query for k in ["오류", "안 됨", "멈춤", "설치", "실행", "전원", "속도", "와이파이"]):
            return "TECH_SUPPORT"
        return None

    async def classify_intent(self, query: str) -> dict:
        try:
            # Rule-based check first for obvious cases
            rule_intent = self._get_rule_based_intent(query)
            
            # Step 1: Retrieve similar historical cases (RAG)
            historical_context = "No historical context available."
            if self.db:
                docs = self.db.similarity_search(query, k=2)
                historical_context = "\n".join([f"- Input: {d.page_content} => Intent: {d.metadata['intent']}" for d in docs])

            # Step 2: LLM Classification with Context
            input_msg = self.prompt.invoke({"query": query, "historical_context": historical_context})
            
            if not os.getenv("OPENAI_API_KEY"):
                # Use rule-based or fallback
                intent = rule_intent or "TECH_SUPPORT"
                return {
                    "intent": intent, 
                    "confidence": 0.8 if rule_intent else 0.5, 
                    "reasoning": f"Rule-based/Mock (Intent: {intent})"
                }
            
            result = await self.llm.ainvoke(input_msg)
            parsed = self.parser.parse(result.content)
            
            # If LLM confidence is low but rule-based is clear, trust rule-based
            if parsed.confidence < 0.7 and rule_intent:
                parsed.intent = rule_intent
                parsed.confidence = 0.9
                parsed.reasoning += " (Overridden by keyword rule)"

            return parsed.dict()
        except Exception as e:
            print(f"Classification Error: {e}")
            fallback_intent = rule_intent or "TECH_SUPPORT"
            return {
                "intent": fallback_intent, 
                "confidence": 0.6 if rule_intent else 0.4, 
                "reasoning": f"Fallback due to error: {str(e)}"
            }
