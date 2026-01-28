import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (query, conversationHistory = []) => {
  try {
    const response = await api.post('/chat', {
      query,
      conversation_history: conversationHistory
    });

    // 백엔드 응답 형식을 프론트엔드 기대 형식에 맞춥니다.
    const data = response.data;
    return {
      message: data.answer,
      requires_approval: data.data && data.data.status === 'pending_approval',
      transaction_id: data.data ? data.data.transaction_id : null,
      approval_message: data.data ? `[${data.data.action_type}]를 승인하시겠습니까?` : null,
      transaction_data: data.data ? {
        "항목": data.data.target_entity,
        "상태": data.data.status,
        "요청": data.data.action_type
      } : null,
      metadata: {
        agent_type: data.type,
        confidence: data.classification_details ? data.classification_details.confidence : 1.0
      }
    };
  } catch (error) {
    console.error('Chat API Error:', error);
    throw error;
  }
};

export const approveTransaction = async (transactionId, approved) => {
  try {
    const response = await api.post('/approve', {
      transaction_id: transactionId,
      approved: approved
    });
    return response.data;
  } catch (error) {
    console.error('Approve API Error:', error);
    throw error;
  }
};

export default api;

