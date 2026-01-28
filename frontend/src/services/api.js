/* 
 * API 통신 서비스
 * Mock 모드: 백엔드 없이 4개 에이전트 테스트 가능
 * 실제 API: 하단 주석 참고
 */

// ==================== Mock 데이터 ====================

const AGENT_RESPONSES = {
  tech_support: {
    keywords: ['로그인', '접속', '오류', '에러', '안됨', '느림'],
    response: (query) => ({
      message: `기술 지원팀입니다.\n\n문제를 확인했습니다:\n1. 브라우저 캐시 삭제\n2. 쿠키 허용 확인\n3. 다른 브라우저로 시도\n\n추가 지원이 필요하시면 말씀해주세요.`,
      requires_approval: false,
      metadata: {
        agent_type: 'tech_support',
        confidence: 0.88
      }
    })
  },

  refund: {
    keywords: ['환불', '취소', '반품'],
    response: (query) => ({
      message: `환불 요청을 확인했습니다.\n\n아래 정보를 확인 후 승인해주세요.`,
      requires_approval: true,
      transaction_id: 'refund_' + Date.now(),
      approval_message: '환불 처리를 승인하시겠습니까?',
      transaction_data: {
        주문번호: 'ORD_2026_001',
        상품명: '무선 이어폰',
        환불금액: '89,000원',
        환불사유: '단순 변심',
        처리기간: '영업일 기준 3-5일',
        환불계좌: '국민은행 ***-****-****'
      },
      metadata: {
        agent_type: 'refund',
        confidence: 0.95
      }
    })
  },

  order: {
    keywords: ['주문', '배송', '조회', 'tracking', '언제'],
    response: (query) => ({
      message: `주문 정보를 조회했습니다.`,
      requires_approval: query.includes('변경') || query.includes('수정'),
      transaction_id: 'order_' + Date.now(),
      approval_message: query.includes('변경') ? '주문 정보 변경을 승인하시겠습니까?' : null,
      transaction_data: query.includes('변경') ? {
        주문번호: 'ORD_2026_002',
        변경항목: '배송지 주소',
        기존값: '서울시 강남구 테헤란로 123',
        변경값: '서울시 서초구 서초대로 456',
        변경사유: '이사로 인한 주소 변경'
      } : {
        주문번호: 'ORD_2026_002',
        상품명: '스마트 워치',
        주문상태: '배송 중',
        배송사: 'CJ대한통운',
        송장번호: '123456789012',
        예상도착: '2026-01-28 (화)'
      },
      metadata: {
        agent_type: 'order',
        confidence: 0.91
      }
    })
  },

  account: {
    keywords: ['계정', '회원', '비밀번호', '탈퇴', '정보수정'],
    response: (query) => ({
      message: `계정 관리 요청을 확인했습니다.`,
      requires_approval: query.includes('탈퇴') || query.includes('삭제'),
      transaction_id: 'account_' + Date.now(),
      approval_message: query.includes('탈퇴') ? '계정 탈퇴를 승인하시겠습니까?' : null,
      transaction_data: query.includes('탈퇴') ? {
        회원ID: 'user_2026_001',
        가입일: '2024-03-15',
        탈퇴사유: '서비스 불만족',
        보유포인트: '5,000P (소멸 예정)',
        진행중주문: '없음',
        경고사항: '탈퇴 후 30일간 재가입 불가'
      } : {
        회원ID: 'user_2026_001',
        이메일: 'user@example.com',
        가입일: '2024-03-15',
        등급: 'VIP',
        포인트: '12,500P'
      },
      metadata: {
        agent_type: 'account',
        confidence: 0.89
      }
    })
  }
};

/*
// Mock 응답 생성 함수
export const sendMessage = async (query, conversationHistory = []) => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // 에이전트 선택
  for (const [agentType, agent] of Object.entries(AGENT_RESPONSES)) {
    for (const keyword of agent.keywords) {
      if (query.includes(keyword)) {
        return agent.response(query);
      }
    }
  }
  
  // 기본 응답
  return {
    message: `안녕하세요! "${query}" 관련 문의를 받았습니다.\n\n지원 가능한 분야:\n- 기술 지원 (로그인, 오류)\n- 환불/취소\n- 주문/배송 조회\n- 계정 관리\n\n구체적으로 어떤 도움이 필요하신가요?`,
    requires_approval: false,
    metadata: {
      agent_type: 'classifier',
      confidence: 0.75
    }
  };
};

export const approveTransaction = async (transactionId, approved) => {
  await new Promise(resolve => setTimeout(resolve, 800));
  
  return {
    status: approved ? 'success' : 'cancelled',
    message: approved 
      ? '승인이 완료되었습니다. 처리까지 1-2 영업일 소요될 수 있습니다.' 
      : '요청이 취소되었습니다.'
  };
};
*/

// ==================== 실제 API 연결 (백엔드 준비 시) ====================
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

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
