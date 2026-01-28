from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

class ClassificationResult(BaseModel):
    intent: str = Field(description="The classification intent: 'tech_support', 'transaction', 'chitchat', or 'off_topic'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief explanation for the classification")

class ClassificationService:
    def __init__(self):
        # Using a placeholder model/API key for now. 
        # In production, ensure OPENAI_API_KEY is set in .env
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful customer service AI. Classify the user input into one of these categories: \n"
                       "- 'tech_support': Questions about how to use the product, errors, or technical issues.\n"
                       "- 'transaction': Requests to cancel orders, change account info, or billing questions.\n"
                       "- 'chitchat': General greetings or polite conversation.\n"
                       "- 'off_topic': Profanity, political statements, or questions unrelated to the service.\n\n"
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
