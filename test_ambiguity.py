import asyncio
import json
from backend.agent import CSAgent

async def test_ambiguity():
    agent = CSAgent()
    query = "기술 지원 가능한 게 뭐가 있어?"
    response = await agent.process_query(query)
    print(f"Query: {query}")
    print(f"Intent: {response['intent']}")
    print(f"Answer: {response['answer']}")
    
    if response['answer']:
        print("✅ SUCCESS: Answer is not None")
    else:
        print("❌ FAILURE: Answer is None")

if __name__ == "__main__":
    asyncio.run(test_ambiguity())
