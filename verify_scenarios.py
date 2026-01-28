import asyncio
import os
from dotenv import load_dotenv
from backend.agent import CSAgent

load_dotenv()

async def verify_scenarios():
    agent = CSAgent()
    
    scenarios = [
        {
            "id": 1,
            "name": "Off-Topic",
            "query": "너 AI 맞아?",
            "expected_intent": "OFF_TOPIC",
            "expected_answer": "해당 문의는 고객 지원 범위에 포함되지 않습니다. 기술 문제, 청구, 주문, 계정 관련 문의 중 어떤 도움이 필요하신가요?"
        },
        {
            "id": 2,
            "name": "Tech Support",
            "query": "전원이 안 켜져요.",
            "expected_intent": "TECH_SUPPORT",
            "expected_answer": "기술 지원 도와드리겠습니다. 기기 모델명과 증상을 자세히 말씀해 주시겠어요?"
        },
        {
            "id": 3,
            "name": "Billing",
            "query": "환불이 안 돼요.",
            "expected_intent": "BILLING",
            "expected_answer": "청구 및 환불 지원 도와드리겠습니다. 주문 번호를 알려주시면 확인해 드릴게요."
        },
        {
            "id": 4,
            "name": "Order",
            "query": "주문 확인하고 싶어요.",
            "expected_intent": "ORDER",
            "expected_answer": "주문 관리 도와드리겠습니다. 최근 30일 이내의 주문 내역을 조회할까요?"
        },
        {
            "id": 5,
            "name": "Account Mgmt",
            "query": "아이디가 기억이 안 나요.",
            "expected_intent": "ACCOUNT_MGMT",
            "expected_answer": "계정 관리 및 본인 인증 도와드리겠습니다."
        }
    ]

    print("\n=== CS Scenarios Verification ===\n")
    
    for scenario in scenarios:
        print(f"Scenario {scenario['id']}: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        
        try:
            result = await agent.process_query(scenario['query'])
            intent = result.get("intent")
            answer = result.get("answer")
            
            print(f"Detected Intent: {intent}")
            print(f"Agent Response: {answer}")
            
            intent_match = intent == scenario['expected_intent']
            answer_match = scenario['expected_answer'] in answer
            
            if intent_match and answer_match:
                print("Result: PASS\n")
            else:
                print("Result: FAIL")
                if not intent_match:
                    print(f"  - Intent mismatch: Expected {scenario['expected_intent']}, got {intent}")
                if not answer_match:
                    print(f"  - Answer mismatch: Expected context including '{scenario['expected_answer']}'")
                print("\n")
                
        except Exception as e:
            print(f"Error processing scenario {scenario['id']}: {e}\n")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in .env. LLM classification may use mock values or fail.")
    asyncio.run(verify_scenarios())
