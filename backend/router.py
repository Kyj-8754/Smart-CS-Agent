from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agent import CSAgent
from services.history import HistoryService
import logging

history_service = HistoryService()


# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CS_Router")

router = APIRouter()
agent = CSAgent()

class FeedbackRequest(BaseModel):
    interaction_id: str
    feedback: str

class ChatRequest(BaseModel):
    query: str
    user_id: str # [NEW] 프론트엔드에서 전달받는 사용자 ID
    conversation_history: Optional[List[Dict[str, Any]]] = []

class TransactionApprovalRequest(BaseModel):
    transaction_id: str
    approved: bool

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"[채팅 요청 수신]: {request.query}")
        
        # 에이전트 호출
        response = await agent.process_query(
            query=request.query, 
            conversation_history=request.conversation_history,
            session_id=request.user_id
        )
        
        # [NEW] Log History
        if request.user_id:
            try:
                history_service.log_interaction(
                    user_id=request.user_id,
                    query=request.query,
                    intent=response.get("intent", "unknown"),
                    response=response
                )
            except Exception as e:
                logger.error(f"[히스토리 저장 실패]: {str(e)}")
        
        logger.info(f"[Agent 응답]: {response}")
        return response
    except Exception as e:
        logger.error(f"[채팅 처리 중 오류]: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve")
async def approve_transaction(request: TransactionApprovalRequest):
    if request.approved:
        # Commit transaction
        result = agent.transaction.execute_transaction(request.transaction_id)
        return result
    else:
        result = agent.transaction.reject_transaction(request.transaction_id)
        return result

@router.get("/history/{user_id}")
async def get_history(user_id: str):
    return history_service.get_user_history(user_id)

@router.post("/feedback")
async def save_feedback(request: FeedbackRequest):
    success = history_service.update_feedback(request.interaction_id, request.feedback)
    if success:
        return {"status": "success", "message": "피드백이 반영되었습니다."}
    else:
        raise HTTPException(status_code=404, detail=f"Interaction ID {request.interaction_id} not found.")