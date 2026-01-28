
import sys
import os
sys.path.append(os.getcwd())

try:
    print("Testing imports...")
    from backend.services.classification import ClassificationService
    print("ClassificationService OK")
    from backend.services.knowledge import KnowledgeService
    print("KnowledgeService OK")
    from backend.services.transaction import TransactionService
    print("TransactionService OK")
    from backend.services.validation import ValidationService
    print("ValidationService OK")
    from backend.agent import CSAgent
    print("CSAgent OK")
    
    agent = CSAgent()
    print("Agent initialized OK")
    
    import asyncio
    async def test():
        print("Processing query...")
        result = await agent.process_query("환불이 안 돼요.")
        print("Result:", result)
    
    asyncio.run(test())
    print("All tests passed!")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
