from backend.services.classification import ClassificationService
from backend.services.knowledge import KnowledgeService
from backend.services.transaction import TransactionService
from backend.services.validation import ValidationService
from langchain_openai import ChatOpenAI

class CSAgent:
    def __init__(self):
        self.classifier = ClassificationService()
        self.knowledge = KnowledgeService()
        self.transaction = TransactionService()
        self.validator = ValidationService()

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
        validation = self.validator.validate_output(response_data)
        if not validation["valid"]:
             response_data["answer"] = validation["safe_response"]
             response_data["blocked"] = True

        return response_data
