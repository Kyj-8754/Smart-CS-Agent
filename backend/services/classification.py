from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

class ClassificationResult(BaseModel):
    intent: str = Field(description="The classification intent: 'OFF_TOPIC', 'TECH_SUPPORT', 'BILLING', 'ORDER', or 'ACCOUNT_MGMT'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the classification")

class ClassificationService:
    def __init__(self):
        # Using a placeholder model/API key for now. 
        # In production, ensure OPENAI_API_KEY is set in .env
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful customer service AI. Classify the user input into one of these categories: \n"
                        "- 'OFF_TOPIC': Questions unrelated to the service (e.g., 'Are you AI?', general chat, profanity).\n"
                        "- 'TECH_SUPPORT': Technical issues, errors, installation, power issues, or how-to-use (Keywords: 오류, 안 됨, 멈춤, 설치, 실행, 전원).\n"
                        "- 'BILLING': Payment, refunds, billing, amounts, receipts (Keywords: 결제, 환불, 청구, 금액, 영수증).\n"
                        "- 'ORDER': Order status, delivery, shipping, cancellation, changes (Keywords: 주문, 배송, 취소, 변경, 택배).\n"
                        "- 'ACCOUNT_MGMT': Login, password, account info, ID, authentication (Keywords: 로그인, 비밀번호, 계정, 아이디, 인증).\n\n"
                        "Use keyword matching and semantic similarity to decide. If multiple categories match, pick the most relevant one.\n"
                        "{format_instructions}"),
            ("user", "{query}")
        ]).partial(format_instructions=self.parser.get_format_instructions())

    async def classify_intent(self, query: str) -> dict:
        try:
            input_msg = self.prompt.invoke({"query": query})
            # This requires an actual API call. If no key is present, this will fail.
            # For now, we'll wrap it or use a mockup if env is missing.
            if not os.getenv("OPENAI_API_KEY"):
                return {
                    "intent": "tech_support", 
                    "confidence": 1.0, 
                    "reasoning": "Mock response (No API Key)"
                }
            
            result = await self.llm.ainvoke(input_msg)
            parsed = self.parser.parse(result.content)
            return parsed.dict()
        except Exception as e:
            print(f"Classification Error: {e}")
            return {
                "intent": "tech_support", 
                "confidence": 0.5, 
                "reasoning": f"Fallback due to error: {str(e)}"
            }
