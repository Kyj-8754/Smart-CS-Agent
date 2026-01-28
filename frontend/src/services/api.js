import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (query, userId, conversationHistory = []) => {
  try {
    const response = await api.post('/chat', {
      query,
      user_id: userId,
      conversation_history: conversationHistory
    });
    return response.data;
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

export const getHistory = async (userId) => {
  try {
    const response = await api.get(`/history/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Get History API Error:', error);
    throw error;
  }
};

export const sendFeedback = async (interactionId, feedback) => {
  try {
    const response = await api.post('/feedback', {
      interaction_id: interactionId,
      feedback: feedback
    });
    return response.data;
  } catch (error) {
    console.error('Feedback API Error:', error);
    throw error;
  }
};

export default api;

