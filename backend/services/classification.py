"""
A파트: 분류용 RAG
부적절한 질문(욕설, 주제 이탈)을 걸러내는 가드레일 로직을 구현
사용자 질문을 과거 질문 cvs(cases.csv)와 대조하여 의도를 파악
"""

import os
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

load_dotenv()

class ClassificationResult(BaseModel):
    intent: str = Field(description="The classification intent: 'OFF_TOPIC', 'TECH_SUPPORT', 'BILLING', 'ORDER', or 'ACCOUNT_MGMT'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the classification using historical cases and keywords")

class ClassificationService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        
        # Initialize RAG for classification using historical cases from csv
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.db = self._initialize_rag()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a customer service AI specialized in classification. \n"
                        "Classify the user input into one of these categories: \n"
                        "- 'OFF_TOPIC': Questions unrelated to the service (e.g., 'Are you AI?', general chat, greetings, profanity, irrelevant questions).\n"
                        "- 'TECH_SUPPORT': Hardware/software technical issues. (Keywords: 오류, 안 됨, 멈춤, 설치, 실행)\n"
                        "- 'BILLING': Payment, refunds, billing, fees. (Keywords: 결제, 환불, 청구, 금액)\n"
                        "- 'ORDER': Order lifecycle (status, delivery, shipping, cancellation, changes). (Keywords: 주문, 배송, 취소, 변경)\n"
                        "- 'ACCOUNT_MGMT': User identity (login, password, account info, ID). (Keywords: 로그인, 비밀번호, 계정, 아이디)\n\n"
                        "Reference historical cases: {historical_context}\n"
                        "Rules:\n"
                        "1. If the query is about whether you are AI or just greetings/chat, classify as 'OFF_TOPIC'.\n"
                        "2. Use keywords as strong signals.\n"
                        "3. Return low confidence (e.g. < 0.5) if the intent is ambiguous.\n"
                        "{format_instructions}"),
            ("user", "{query}")
        ]).partial(format_instructions=self.parser.get_format_instructions())

    def _initialize_rag(self):
        """Loads historical cases from CSV and initializes FAISS."""
        try:
            # Assuming the script runs from project root or backend directory
            csv_path = os.path.join(os.getcwd(), "backend", "data", "cases.csv")
            if not os.path.exists(csv_path):
                # Fallback check
                csv_path = os.path.join(os.getcwd(), "data", "cases.csv")
            
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                documents = []
                for _, row in df.iterrows():
                    documents.append(Document(
                        page_content=row['page_content'],
                        metadata={"intent": row['intent']}
                    ))
                return FAISS.from_documents(documents, self.embeddings)
            else:
                print(f"Warning: cases.csv not found at {csv_path}")
                return None
        except Exception as e:
            print(f"Classification RAG Init Error: {e}")
            return None

    def _detect_guardrails(self, query: str) -> bool:
        """Detects profanity or inappropriate chat."""
        # Simple placeholder for profanity/chat detection
        bad_words = ["욕설", "나쁜말", "바보"] # Example placeholder
        if any(word in query for word in bad_words):
            return True
        # Check for "Are you AI?" or generic greetings that are off-topic
        off_topic_patterns = ["너 ai", "누구니", "심심해", "안녕"]
        if any(pattern in query.lower() for pattern in off_topic_patterns):
            return True
        return False

    def _get_keyword_intent(self, query: str) -> str:
        """Rule-based keyword detection."""
        query = query.lower()
        keywords = {
            "TECH_SUPPORT": ["오류", "안 됨", "멈춤", "설치", "실행", "전원", "안켜져", "안져요"],
            "BILLING": ["결제", "환불", "청구", "금액"],
            "ORDER": ["주문", "배송", "취소", "변경"],
            "ACCOUNT_MGMT": ["로그인", "비밀번호", "계정", "아이디", "가 기억이 안나", "찾기"]
        }
        for intent, kws in keywords.items():
            if any(kw in query for kw in kws):
                return intent
        return None

    async def classify_intent(self, query: str) -> dict:
        try:
            # Step 1: Guardrail Check
            if self._detect_guardrails(query):
                return {
                    "intent": "OFF_TOPIC",
                    "confidence": 0.4,
                    "reasoning": "Detected as off-topic or guardrail violation."
                }

            # Step 2: Keyword match (Strong heuristic)
            kw_intent = self._get_keyword_intent(query)

            # Step 3: Retrieve similar cases
            historical_context = "No historical context available."
            if self.db:
                docs = self.db.similarity_search(query, k=3)
                historical_context = "\n".join([f"- Case: {d.page_content} => Intent: {d.metadata['intent']}" for d in docs])

            # Step 4: LLM Classification
            input_msg = self.prompt.invoke({"query": query, "historical_context": historical_context})
            
            if not os.getenv("OPENAI_API_KEY"):
                # Mock response if no API key
                intent = kw_intent or "OFF_TOPIC"
                return {
                    "intent": intent, 
                    "confidence": 0.9 if kw_intent else 0.4, 
                    "reasoning": f"Keyword/Mock Result: {intent}"
                }
            
            result = await self.llm.ainvoke(input_msg)
            parsed = self.parser.parse(result.content)
            
            # Hybrid: Trust keyword if confidence is low
            if parsed.confidence < 0.6 and kw_intent:
                parsed.intent = kw_intent
                parsed.confidence = 0.9
                parsed.reasoning += " (Overridden by keyword rule)"

            return parsed.dict()
        except Exception as e:
            print(f"Classification Error: {e}")
            return {
                "intent": "OFF_TOPIC", 
                "confidence": 0.0, 
                "reasoning": f"Error: {str(e)}"
            }
