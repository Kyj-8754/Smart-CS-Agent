"""
B파트: 통합 지식 서비스 (All-in-One)
- 대화 맥락 관리 (ConversationManager 통합)
- FAQ 검색 (KnowledgeService)
- 규칙 기반 판단
"""

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 대화 맥락 관리자 ====================

class ConversationManager:
    """
    대화 맥락 관리
    
    기능:
    1. 세션별 대화 기록 저장
    2. 지시 대명사 해결
    3. 시도한 해결책 추적
    """
    
    def __init__(self):
        self.sessions = {}
    
    def add_turn(self, 
                 session_id: str, 
                 user_query: str, 
                 bot_response: str,
                 suggested_action: str = None,
                 faq_id: str = None):
        """대화 턴 추가"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'current_issue': None,
                'tried_solutions': [],
                'last_suggestion': None,
                'created_at': datetime.now()
            }
        
        self.sessions[session_id]['history'].append({
            'timestamp': datetime.now(),
            'user_query': user_query,
            'bot_response': bot_response,
            'suggested_action': suggested_action,
            'faq_id': faq_id
        })
        
        if suggested_action:
            self.sessions[session_id]['last_suggestion'] = suggested_action
            self.sessions[session_id]['tried_solutions'].append(suggested_action)
        
        if not self.sessions[session_id]['current_issue']:
            self.sessions[session_id]['current_issue'] = self._extract_issue(user_query)
    
    def _extract_issue(self, query: str) -> str:
        """현재 문제 추출"""
        issues = {
            '인터넷': 'internet_issue',
            '와이파이': 'wifi_issue',
            '앱': 'app_issue',
            '느림': 'slow_issue',
            '청구': 'billing_issue',
            '주문': 'order_issue',
            '로그인': 'login_issue'
        }
        
        for keyword, issue in issues.items():
            if keyword in query:
                return issue
        
        return 'general_issue'
    
    def resolve_references(self, session_id: str, query: str) -> str:
        """지시 대명사 해결"""
        if session_id not in self.sessions:
            return query
        
        context = self.sessions[session_id]
        
        if not context['last_suggestion']:
            return query
        
        references = {
            '그거': context['last_suggestion'],
            '그것': context['last_suggestion'],
            '이거': context['last_suggestion'],
            '이것': context['last_suggestion'],
            '저거': context['last_suggestion'],
            '저것': context['last_suggestion'],
            '그렇게': context['last_suggestion'],
            '이렇게': context['last_suggestion']
        }
        
        resolved = query
        for ref, actual in references.items():
            if ref in resolved:
                resolved = resolved.replace(ref, actual)
                
                if actual not in context['tried_solutions']:
                    context['tried_solutions'].append(actual)
        
        if resolved != query:
            logger.info(f"[맥락 해결] '{query}' → '{resolved}'")
        
        return resolved
    
    def get_context_summary(self, session_id: str) -> Dict:
        """현재 맥락 요약"""
        if session_id not in self.sessions:
            return {'has_context': False}
        
        context = self.sessions[session_id]
        
        return {
            'has_context': True,
            'turn_count': len(context['history']),
            'current_issue': context['current_issue'],
            'tried_solutions': context['tried_solutions'],
            'last_suggestion': context['last_suggestion']
        }
    
    def add_context_to_prompt(self, session_id: str, query: str) -> str:
        """AI 프롬프트에 맥락 추가"""
        if session_id not in self.sessions:
            return query
        
        context = self.sessions[session_id]
        
        if not context['tried_solutions']:
            return query
        
        context_text = f"[이전 대화 맥락]\n"
        context_text += f"- 현재 문제: {context['current_issue']}\n"
        context_text += f"- 이미 시도한 방법: {', '.join(context['tried_solutions'])}\n\n"
        context_text += f"[현재 질문]\n{query}"
        
        return context_text
    
    def clear_session(self, session_id: str):
        """세션 삭제"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_old_sessions(self, hours: int = 24):
        """오래된 세션 정리"""
        now = datetime.now()
        to_delete = []
        
        for session_id, context in self.sessions.items():
            age = (now - context['created_at']).total_seconds() / 3600
            if age > hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            del self.sessions[session_id]
        
        return len(to_delete)


# ==================== 지식 서비스 ====================

class KnowledgeService:
    """
    통합 지식 서비스
    
    기능:
    - FAQ 검색 (FAISS)
    - 규칙 기반 애매모호 판단
    - 대화 맥락 유지
    - AI fallback (선택)
    """
    
    def __init__(self, 
                 csv_path: str = "data/faq_database.csv",
                 model_name: str = "jhgan/ko-sroberta-multitask",
                 use_ai_fallback: bool = False,
                 enable_conversation: bool = True):
        
        logger.info("=" * 60)
        logger.info("B파트: 통합 지식 서비스 초기화")
        logger.info("=" * 60)
        
        self.csv_path = csv_path
        self.use_ai_fallback = use_ai_fallback
        self.enable_conversation = enable_conversation
        
        # 대화 맥락 관리자
        if enable_conversation:
            self.conversation = ConversationManager()
            logger.info("  ✅ 대화 맥락 관리 활성화")
        else:
            self.conversation = None
        
        # 임베딩 모델
        logger.info(f"임베딩 모델 로드: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"  ✅ 임베딩 차원: {self.dimension}")
        except Exception as e:
            logger.error(f"  ❌ 모델 로드 실패: {e}")
            raise
        
        # CSV 로드
        self.faq_df = self._load_csv()
        
        # FAISS 인덱스
        self.index = None
        if not self.faq_df.empty:
            self.index = self._build_index()
        
        # AI API (선택)
        self.ai_client = None
        if use_ai_fallback:
            self._setup_ai_api()
        
        logger.info("✅ 통합 지식 서비스 초기화 완료\n")
    
    def _setup_ai_api(self):
        """AI API 설정"""
        try:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                logger.warning("⚠️  OpenAI API 키 없음")
                self.use_ai_fallback = False
                return
            
            from openai import OpenAI
            self.ai_client = OpenAI(api_key=key)
            logger.info("  ✅ AI API 설정 완료")
            
        except ImportError:
            logger.warning("⚠️  openai 패키지 없음")
            self.use_ai_fallback = False
        except Exception as e:
            logger.warning(f"⚠️  AI API 설정 실패: {e}")
            self.use_ai_fallback = False
    
    def _load_csv(self) -> pd.DataFrame:
        """CSV 로드"""
        csv_file = Path(self.csv_path)
        
        if not csv_file.exists():
            logger.error(f"❌ CSV 파일 없음: {self.csv_path}")
            raise FileNotFoundError(f"FAQ 파일을 찾을 수 없습니다: {self.csv_path}")
        
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            logger.info(f"  ✅ CSV 로드: {len(df)}개 FAQ")
            
            required = ['id', 'category', 'question', 'answer']
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(f"필수 컬럼 누락: {missing}")
            
            return df
            
        except Exception as e:
            logger.error(f"  ❌ CSV 로드 실패: {e}")
            raise
    
    def _build_index(self):
        """FAISS 인덱스 생성"""
        logger.info("FAISS 인덱스 생성 중...")
        
        try:
            texts = []
            for idx, row in self.faq_df.iterrows():
                text = row['question']
                if 'keywords' in self.faq_df.columns and pd.notna(row['keywords']):
                    text += " " + row['keywords'].replace(',', ' ')
                texts.append(text)
            
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            faiss.normalize_L2(embeddings)
            
            index = faiss.IndexFlatIP(self.dimension)
            index.add(embeddings)
            
            logger.info(f"  ✅ FAISS 인덱스: {index.ntotal}개 벡터")
            return index
            
        except Exception as e:
            logger.error(f"  ❌ 인덱스 생성 실패: {e}")
            raise
    
    def _is_ambiguous(self, query: str, similarity_score: float, category: str) -> Tuple[bool, str]:
        """규칙 기반 애매모호 판단"""
        if similarity_score < 0.6:
            
            ambiguous_patterns = {
                '주어 없음': ['느려요', '안 돼요', '안 됩니다', '이상해요', '문제', '오류예요'],
                '지시어': ['그거', '이거', '저거', '이것', '그것', '저것'],
                '불완전': ['왜', '뭐', '어떻게', '언제']
            }
            
            for pattern_type, patterns in ambiguous_patterns.items():
                if any(pattern in query for pattern in patterns):
                    
                    specific_nouns = {
                        'tech_support': ['인터넷', '와이파이', '앱', '기기', '화면', '소리'],
                        'billing_support': ['청구서', '요금', '결제', '환불', '영수증'],
                        'order_management': ['주문', '배송', '교환', '반품', '취소'],
                        'account_management': ['비밀번호', '로그인', '계정', '회원', '가입']
                    }
                    
                    category_nouns = specific_nouns.get(category, [])
                    has_specific = any(noun in query for noun in category_nouns)
                    
                    if not has_specific:
                        return True, f"{pattern_type}"
        
        return False, ""
    
    def _generate_clarification_question(self, category: str, faq_results: List[Dict]) -> str:
        """명확화 질문 생성"""
        templates = {
            'tech_support': {
                'title': '기술 지원',
                'options': [
                    '🌐 인터넷/네트워크 문제',
                    '📱 앱/프로그램 문제',
                    '💻 기기 하드웨어 문제',
                    '🔊 소리/화면 문제'
                ]
            },
            'billing_support': {
                'title': '청구 지원',
                'options': [
                    '📋 청구서 확인',
                    '💳 결제 문제',
                    '💰 환불 요청',
                    '🔄 자동결제 관리'
                ]
            },
            'order_management': {
                'title': '주문 관리',
                'options': [
                    '❌ 주문 취소',
                    '📦 배송 문의',
                    '🔄 교환/반품',
                    '📍 배송지 변경'
                ]
            },
            'account_management': {
                'title': '계정 관리',
                'options': [
                    '🔐 비밀번호 문제',
                    '🚪 로그인 문제',
                    '✏️  정보 수정',
                    '🚫 회원 탈퇴'
                ]
            }
        }
        
        template = templates.get(category, {
            'title': '문의',
            'options': ['기타 문의']
        })
        
        question = f"**{template['title']}** 관련 문의시군요!\n"
        question += "구체적으로 어떤 도움이 필요하신가요?\n\n"
        
        for i, opt in enumerate(template['options'], 1):
            question += f"{i}️⃣  {opt}\n"
        
        question += f"{len(template['options'])+1}️⃣  기타\n\n"
        question += "번호를 선택하거나 자세히 설명해주세요."
        
        return question
    
    def _is_out_of_scope(self, query: str, similarity_score: float) -> bool:
        """범위 밖 판단"""
        if similarity_score < 0.25:
            off_topic = [
                '날씨', '뉴스', '주식', '맛집', '여행', '영화', 
                '드라마', '음악', '게임', '요리', '운동'
            ]
            return any(keyword in query for keyword in off_topic)
        return False
    
    def search_knowledge(self, 
                        query: str, 
                        category: str = None,
                        session_id: str = None) -> Dict:
        """
        지식 검색 (대화 맥락 지원)
        
        Args:
            query: 사용자 질문
            category: 분류된 카테고리
            session_id: 세션 ID (대화 맥락용)
        
        Returns:
            {
                "answer": 답변,
                "needs_clarification": 재질문 필요,
                "clarification_question": 재질문,
                "confidence": 신뢰도,
                "context_used": 맥락 사용 여부
            }
        """
        original_query = query
        
        # 1. 대화 맥락에서 지시 대명사 해결
        if self.enable_conversation and session_id and self.conversation:
            resolved_query = self.conversation.resolve_references(session_id, query)
            
            if resolved_query != query:
                logger.info(f"[맥락] '{query}' → '{resolved_query}'")
                query = resolved_query
        
        if self.index is None:
            return {
                "answer": "죄송합니다. 지식 베이스를 사용할 수 없습니다.",
                "needs_clarification": False,
                "out_of_scope": False
            }
        
        try:
            # 2. FAQ 검색
            results = self._search_faq(query, category=category, top_k=3)
            
            if not results:
                return {
                    "answer": self._generate_out_of_scope_message(),
                    "needs_clarification": False,
                    "out_of_scope": True,
                    "confidence": 0.0
                }
            
            best_match = results[0]
            score = best_match['similarity_score']
            matched_category = best_match['category']
            
            # 3. 범위 밖 체크
            if self._is_out_of_scope(query, score):
                logger.info(f"🚫 범위 밖 (유사도: {score:.3f})")
                return {
                    "answer": self._generate_out_of_scope_message(),
                    "needs_clarification": False,
                    "out_of_scope": True,
                    "confidence": score
                }
            
            # 4. 애매모호 체크
            is_ambig, reason = self._is_ambiguous(query, score, matched_category)
            
            if is_ambig:
                logger.info(f"❓ 애매모호 (유사도: {score:.3f}, 이유: {reason})")
                return {
                    "answer": None,
                    "needs_clarification": True,
                    "clarification_question": self._generate_clarification_question(
                        matched_category, results
                    ),
                    "out_of_scope": False,
                    "confidence": score
                }
            
            # 5. 답변 생성
            if score >= 0.70:
                logger.info(f"✅ FAQ 매칭 (유사도: {score:.3f})")
                answer = best_match['answer']
                used_ai = False
                suggested_action = self._extract_first_action(answer)
            
            elif score >= 0.50:
                logger.info(f"⚠️  중간 매칭 (유사도: {score:.3f})")
                answer = f"{best_match['answer']}\n\n💡 추가 문의: 고객센터(1234-5678)"
                used_ai = False
                suggested_action = self._extract_first_action(answer)
            
            else:
                # AI 사용 (선택)
                if self.use_ai_fallback and self.ai_client:
                    logger.info(f"🤖 AI 호출 (유사도: {score:.3f})")
                    
                    if self.enable_conversation and session_id and self.conversation:
                        extended_query = self.conversation.add_context_to_prompt(session_id, query)
                    else:
                        extended_query = query
                    
                    answer = self._generate_ai_answer(extended_query, results)
                    used_ai = True
                    suggested_action = None
                else:
                    logger.info(f"❌ 낮은 매칭 (유사도: {score:.3f})")
                    answer = "명확한 답변을 찾지 못했습니다. 고객센터(1234-5678)로 문의해주세요."
                    used_ai = False
                    suggested_action = None
            
            # 6. 대화 기록 저장
            if self.enable_conversation and session_id and self.conversation:
                self.conversation.add_turn(
                    session_id=session_id,
                    user_query=original_query,
                    bot_response=answer,
                    suggested_action=suggested_action,
                    faq_id=best_match.get('faq_id')
                )
            
            return {
                "answer": answer,
                "needs_clarification": False,
                "out_of_scope": False,
                "confidence": score,
                "used_ai": used_ai,
                "matched_faq_id": best_match['faq_id'],
                "context_used": original_query != query
            }
                
        except Exception as e:
            logger.error(f"검색 오류: {e}")
            return {
                "answer": "검색 중 오류가 발생했습니다.",
                "needs_clarification": False,
                "out_of_scope": False
            }
    
    def _extract_first_action(self, answer: str) -> Optional[str]:
        """답변에서 첫 번째 제안 조치 추출"""
        match = re.search(r'1\.\s*([^\n]+)', answer)
        if match:
            action = match.group(1).strip()
            action = re.sub(r'\([^)]*\)', '', action).strip()
            return action[:50]
        return None
    
    def _search_faq(self, query: str, category: str = None, top_k: int = 3) -> List[Dict]:
        """FAQ 검색"""
        if self.index is None:
            return []
        
        try:
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            
            scores, indices = self.index.search(query_embedding, min(top_k * 2, len(self.faq_df)))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if score < 0.2:
                    continue
                
                faq_row = self.faq_df.iloc[idx]
                
                if category and faq_row['category'] != category:
                    continue
                
                results.append({
                    'faq_id': faq_row['id'],
                    'category': faq_row['category'],
                    'question': faq_row['question'],
                    'answer': faq_row['answer'],
                    'similarity_score': float(score)
                })
                
                if len(results) >= top_k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"FAQ 검색 실패: {e}")
            return []
    
    def _generate_ai_answer(self, query: str, faq_results: List[Dict]) -> str:
        """AI 답변 생성"""
        if not self.ai_client:
            return "AI 답변 생성 불가"
        
        try:
            context = ""
            if faq_results:
                context = "참고 FAQ:\n"
                for faq in faq_results[:2]:
                    context += f"Q: {faq['question']}\nA: {faq['answer'][:100]}...\n\n"
            
            response = self.ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "친절한 고객 지원 AI입니다."},
                    {"role": "user", "content": f"{context}\n질문: {query}"}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            answer = response.choices[0].message.content.strip()
            answer += "\n\n🤖 (AI 생성 답변)"
            return answer
            
        except Exception as e:
            logger.error(f"AI 생성 실패: {e}")
            return "AI 답변 생성 중 오류가 발생했습니다."
    
    def _generate_out_of_scope_message(self) -> str:
        """범위 밖 메시지"""
        return """죄송합니다. 다음 분야만 지원 가능합니다:

✅ **지원 가능 분야**
• 🛠️  기술 지원 (인터넷, 앱, 기기 문제)
• 💳 청구 지원 (요금, 결제, 환불)
• 📦 주문 관리 (주문, 배송, 교환/반품)
• 👤 계정 관리 (로그인, 비밀번호, 회원정보)

고객센터: 1234-5678"""
    
    def get_conversation_summary(self, session_id: str) -> Dict:
        """대화 맥락 요약"""
        if not self.enable_conversation or not self.conversation:
            return {'has_context': False}
        
        return self.conversation.get_context_summary(session_id)


# ==================== 테스트 ====================

def test_integrated_service():
    """통합 서비스 테스트"""
    print("\n" + "=" * 70)
    print("통합 지식 서비스 테스트 (All-in-One)")
    print("=" * 70)
    
    service = KnowledgeService(
        csv_path="faq_database_48.csv",
        enable_conversation=True
    )
    
    session_id = "test_session_001"
    
    # 대화 1
    print("\n[대화 1]")
    query1 = "인터넷이 안 돼요"
    result1 = service.search_knowledge(query1, "tech_support", session_id)
    
    print(f"사용자: {query1}")
    print(f"봇: {result1['answer'][:100]}...")
    
    # 대화 2 - 지시 대명사
    print("\n" + "=" * 70)
    print("[대화 2]")
    query2 = "그거 했는데도 안 돼요"
    result2 = service.search_knowledge(query2, "tech_support", session_id)
    
    print(f"사용자: {query2}")
    print(f"맥락 사용: {result2.get('context_used')}")
    print(f"봇: {result2['answer'][:100]}...")
    
    # 대화 3
    print("\n" + "=" * 70)
    print("[대화 3]")
    query3 = "이것도 안 돼요"
    result3 = service.search_knowledge(query3, "tech_support", session_id)
    
    print(f"사용자: {query3}")
    print(f"맥락 사용: {result3.get('context_used')}")
    
    summary = service.get_conversation_summary(session_id)
    print(f"시도한 방법: {summary.get('tried_solutions', [])}")
    
    print("\n" + "=" * 70)
    print("✅ 테스트 완료!")
    print("=" * 70)


if __name__ == "__main__":
    test_integrated_service()