import asyncio
import os
import sys

# Ensure the backend directory is in the path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from agent import CSAgent

async def test():
    agent = CSAgent()
    test_cases = [
        "너 AI 맞아?", # Scenario 1: OFF_TOPIC
        "전원이 안 켜져요.", # Scenario 2: TECH_SUPPORT
        "환불이 안 되요.", # Scenario 3: BILLING
        "주문 확인 하고 싶어요.", # Scenario 4: ORDER
        "아이디가 기억이 안나요." # Scenario 5: ACCOUNT_MGMT
    ]
    
    print("=== Full Agent Pipeline Test Starts ===")
    for query in test_cases:
        try:
            response = await agent.process_query(query)
            print(f"Query: {query}")
            print(f"Intent: {response['intent']}")
            print(f"Response: {response['message']}")
            print("-" * 30)
        except Exception as e:
            print(f"Error testing query '{query}': {e}")
    print("=== Full Agent Pipeline Test Ends ===")

if __name__ == "__main__":
    asyncio.run(test())
