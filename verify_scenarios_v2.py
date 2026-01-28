import asyncio
import os
from dotenv import load_dotenv
from backend.agent import CSAgent

load_dotenv()

async def verify_v2():
    agent = CSAgent()
    
    test_cases = [
        {
            "id": 1,
            "name": "Guardrail (Nonsense)",
            "query": "어제 먹은 사과가 너무 맛있었어.",
            "expected_intent": "OFF_TOPIC",
            "expected_answer": "해당 문의는 고객 지원 범위에 포함되지 않습니다."
        },
        {
            "id": 2,
            "name": "RAG-based Classification (Account)",
            "query": "아이디가 기억이 안나요.",
            "expected_intent": "ACCOUNT_MGMT",
            "expected_answer": "계정 관리 도와드리겠습니다."
        },
        {
            "id": 3,
            "name": "Scenario 1 (Off-Topic)",
            "query": "너 AI 맞아?",
            "expected_intent": "OFF_TOPIC",
            "expected_answer": "해당 문의는 고객 지원 범위에 포함되지 않습니다."
        },
        {
            "id": 4,
            "name": "Scenario 2 (Tech Support)",
            "query": "전원이 안 켜져요.",
            "expected_intent": "TECH_SUPPORT",
            "expected_answer": "기술 지원 도와드리겠습니다."
        }
    ]

    print("\n=== CS Scenarios v2 Verification ===\n")
    
    for case in test_cases:
        print(f"Test {case['id']}: {case['name']}")
        print(f"Query: {case['query']}")
        
        result = await agent.process_query(case['query'])
        intent = result.get("intent")
        answer = result.get("answer")
        
        print(f"Detected Intent: {intent}")
        print(f"Agent Response: {answer}")
        
        if intent == case['expected_intent'] and case['expected_answer'] in answer:
            print("Result: PASS\n")
        else:
            print(f"Result: FAIL (Expected Intent: {case['expected_intent']}, Expected Answer Context: {case['expected_answer']})\n")

if __name__ == "__main__":
    asyncio.run(verify_v2())
