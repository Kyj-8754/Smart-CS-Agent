import asyncio
import json
import logging
from backend.agent import CSAgent

# Force logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def debug_query():
    agent = CSAgent()
    query = "환불이 안 돼요."
    print(f"\n--- Debugging Query: {query} ---")
    
    # 1. Check Classification
    classification = await agent.classifier.classify_intent(query)
    print(f"Classification Intent: {classification.get('intent')}")
    print(f"Confidence: {classification.get('confidence')}")
    
    # 2. Check Knowledge Service RAG (With Category)
    intent_map = {
        "TECH_SUPPORT": "tech_support",
        "BILLING": "billing_support",
        "ORDER": "order_management",
        "ACCOUNT_MGMT": "account_management"
    }
    category = intent_map.get(classification.get('intent'))
    rag_result = agent.knowledge.search_knowledge(query, category=category)
    
    answer = rag_result.get('answer')
    if answer:
        print(f"\nRAG Answer: {answer[:100]}...")
    else:
        print(f"\nRAG Answer: None (Clarification expected)")
    
    print(f"Matched FAQ ID: {rag_result.get('matched_faq_id')}")
    print(f"Confidence: {rag_result.get('confidence')}")
    
    # 3. Process Query through full Agent
    response = await agent.process_query(query)
    print(f"\nFinal Agent Response Intent: {response['intent']}")
    print(f"Final Agent Answer: {response['answer'][:100]}...")

if __name__ == "__main__":
    asyncio.run(debug_query())
