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

export default api;

