from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import CSAgent

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
        return response
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
