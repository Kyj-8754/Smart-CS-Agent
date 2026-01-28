import asyncio
import json
from backend.agent import CSAgent

async def verify_fixes():
    agent = CSAgent()
    
    # Test 1: Ambiguity handling
    query1 = "기술 지원 가능한 게 뭐가 있어?"
    resp1 = await agent.process_query(query1)
    print(f"Query 1: {query1}")
    print(f"Answer: {resp1['answer']}")
    assert resp1['answer'] is not None, "Answer should not be None"
    
    # Test 2: General Complaint (No Transaction)
    query2 = "환불이 안 돼요."
    resp2 = await agent.process_query(query2)
    print(f"\nQuery 2: {query2}")
    print(f"Answer: {resp2['answer']}")
    has_txn = "data" in resp2
    print(f"Has Transaction: {has_txn}")
    assert not has_txn, "Complaint should NOT trigger a transaction dialog"
    
    # Test 3: Explicit Action (Transaction Required)
    query3 = "환불 신청해줘"
    resp3 = await agent.process_query(query3)
    print(f"\nQuery 3: {query3}")
    print(f"Action Type: {resp3.get('data', {}).get('action_type')}")
    has_txn = "data" in resp3
    print(f"Has Transaction: {has_txn}")
    assert has_txn, "Action request SHOULD trigger a transaction dialog"
    
    print("\n✅ ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(verify_fixes())
