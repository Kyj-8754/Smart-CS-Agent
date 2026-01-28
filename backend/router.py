from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agent import CSAgent

router = APIRouter()
agent = CSAgent()

class ChatRequest(BaseModel):
    query: str
    conversation_history: Optional[List[Dict[str, Any]]] = []

class TransactionApprovalRequest(BaseModel):
    transaction_id: str
    approved: bool

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = await agent.process_query(request.query, request.conversation_history)
        
        # 프론트엔드가 기대하는 형식으로 변환
        # 프론트엔드는 data.answer를 기대하므로 message를 answer로 매핑
        transformed_response = {
            "answer": response.get("message", ""),
            "type": response.get("type", "unknown"),
            "intent": response.get("intent", ""),
            "classification_details": response.get("classification_details", {}),
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