import asyncio
import os
import sys

# Ensure the backend directory is in the path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.classification import ClassificationService

async def test():
    service = ClassificationService()
    test_cases = [
        "너 AI 맞아?", # Scenario 1
        "전원이 안 켜져요.", # Scenario 2
        "환불이 안 되요.", # Scenario 3
        "주문 확인 하고 싶어요.", # Scenario 4
        "아이디가 기억이 안나요." # Scenario 5
    ]
    
    print("=== Classification Test Starts ===")
    for query in test_cases:
        try:
            result = await service.classify_intent(query)
            print(f"Query: {query}")
            print(f"Result: {result}")
            print("-" * 30)
        except Exception as e:
            print(f"Error testing query '{query}': {e}")
    print("=== Classification Test Ends ===")

if __name__ == "__main__":
    asyncio.run(test())
