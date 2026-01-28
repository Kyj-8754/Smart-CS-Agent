from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import CSAgent

router = APIRouter()
agent = CSAgent()

class ChatRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, Any]]] = []
    session_id: Optional[str] = "test_user_001"

class TransactionApprovalRequest(BaseModel):
    transaction_id: str
    approved: bool

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        s_id = getattr(request, 'session_id', "default_user")

        # 에이전트 호출 시 session_id 전달
        response = await agent.process_query(
            request.query, 
            request.conversation_history,
            session_id=s_id  # 님의 B파트 기능을 위해 추가
        )
        
        transformed_response = {
            "answer": response.get("message", ""),
            "type": response.get("type", "unknown"),
            "intent": response.get("intent", ""),
            "classification_details": response.get("classification_details", {}),
            "from_cache": response.get("from_cache", False), # B파트의 캐시 사용 여부 추가
            "data": response.get("data", None)
        }
        
        return transformed_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve")
async def approve_transaction(request: TransactionApprovalRequest):
    if request.approved:
        # Commit transaction
        result = agent.transaction.execute_transaction(request.transaction_id)
        return result
    else:
        return {"status": "cancelled", "message": "Transaction cancelled by user."}