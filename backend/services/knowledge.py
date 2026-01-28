"""
B파트: 캐시 시스템이 추가된 RAG
- 사용자 피드백 기반 캐시
- 검증된 답변 재사용
- LLM 비용 절감
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
import time
import json
import hashlib
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 캐시 관리자 ====================

class AnswerCache:
    """
    검증된 답변 캐시 시스템
    
    기능:
    1. 질문-답변 쌍 저장
    2. 사용자 피드백 기반 캐싱
    3. 캐시 히트 시 즉시 반환 (LLM 호출 없음)
    """
    
    def __init__(self, cache_file: str = "backend/data/answer_cache.json"):
        """캐시 파일 초기화 - 여러 경로 탐색"""
        base_dir = Path(__file__).parent.parent
        
        # 가능한 경로들 순서대로 탐색
        search_paths = [
            Path(cache_file),
            base_dir / "data" / "answer_cache.json",
            Path(os.getcwd()) / "backend" / "data" / "answer_cache.json",
            Path(os.getcwd()) / "data" / "answer_cache.json"
        ]
        
        # 존재하는 파일 찾기 또는 첫 번째 경로 사용
        self.cache_file = None
        for path in search_paths:
            if path.exists():
                self.cache_file = path
                break
        
        if not self.cache_file:
            self.cache_file = search_paths[1]
            
        self.cache = self._load_cache()
        self.embeddings_cache = {}
        logger.info(f"  ✅ 답변 캐시 초기화 ({len(self.cache)}개 저장됨)")
    
    def _load_cache(self) -> Dict:
        """캐시 파일 로드"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
    
    def _get_query_hash(self, query: str, category: str = None) -> str:
        """질문의 해시값 생성 - 공백/대소문자 무시"""
        clean_query = query.strip().lower().replace(" ", "")
        key = f"{category}:{clean_query}" if category else clean_query
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, query: str, category: str = None, similarity_threshold: float = 0.95) -> Optional[Dict]:
        """캐시에서 답변 조회"""
        query_hash = self._get_query_hash(query, category)
        
        if query_hash in self.cache:
            cached_item = self.cache[query_hash]
            
            if cached_item.get('verified', False):
                logger.info(f"  💾 캐시 히트! (정확한 매칭)")
                cached_item['cache_hit'] = True
                cached_item['cache_type'] = 'exact'
                return cached_item
        
        return None
    
    def add(self, query: str, answer: str, category: str = None, verified: bool = False, feedback_score: int = 0, metadata: Dict = None) -> str:
        """캐시에 답변 추가"""
        query_hash = self._get_query_hash(query, category)
        
        self.cache[query_hash] = {
            'query': query,
            'answer': answer,
            'category': category,
            'verified': verified,
            'feedback_score': feedback_score,
            'created_at': datetime.now().isoformat(),
            'hit_count': 0,
            'metadata': metadata or {}
        }
        
        self._save_cache()
        logger.info(f"  💾 캐시 추가: {query[:30]}... (verified={verified})")
        
        return query_hash
    
    def verify(self, query: str, category: str = None, feedback_score: int = 5):
        """사용자가 답변을 승인"""
        query_hash = self._get_query_hash(query, category)
        
        if query_hash in self.cache:
            self.cache[query_hash]['verified'] = True
            self.cache[query_hash]['feedback_score'] = feedback_score
            self.cache[query_hash]['verified_at'] = datetime.now().isoformat()
            
            self._save_cache()
            logger.info(f"  ✅ 답변 승인: {query[:30]}... (점수: {feedback_score})")
        else:
            logger.warning(f"  ⚠️  캐시에 없는 질문: {query[:30]}...")
    
    def reject(self, query: str, category: str = None, reason: str = None):
        """사용자가 답변을 거부"""
        query_hash = self._get_query_hash(query, category)
        
        if query_hash in self.cache:
            self.cache[query_hash]['verified'] = False
            self.cache[query_hash]['rejected'] = True
            self.cache[query_hash]['rejected_at'] = datetime.now().isoformat()
            self.cache[query_hash]['rejection_reason'] = reason
            
            self._save_cache()
            logger.info(f"  ❌ 답변 거부: {query[:30]}...")
    
    def increment_hit_count(self, query: str, category: str = None):
        """캐시 히트 카운트 증가"""
        query_hash = self._get_query_hash(query, category)
        
        if query_hash in self.cache:
            self.cache[query_hash]['hit_count'] = self.cache[query_hash].get('hit_count', 0) + 1
            self.cache[query_hash]['last_used'] = datetime.now().isoformat()
            self._save_cache()
    
    def get_stats(self) -> Dict:
        """캐시 통계"""
        total = len(self.cache)
        verified = sum(1 for item in self.cache.values() if item.get('verified'))
        rejected = sum(1 for item in self.cache.values() if item.get('rejected'))
        pending = total - verified - rejected
        
        total_hits = sum(item.get('hit_count', 0) for item in self.cache.values())
        
        return {
            'total_cached': total,
            'verified': verified,
            'rejected': rejected,
            'pending': pending,
            'total_cache_hits': total_hits,
            'cache_hit_rate': total_hits / max(total, 1)
        }


# ==================== 대화 맥락 관리자 ====================

class ConversationManager:
    """대화 맥락 관리"""
    
    def __init__(self):
        self.sessions = {}
    
    def add_turn(self, session_id: str, user_query: str, bot_response: str, suggested_action: str = None, faq_ids: List[str] = None, from_cache: bool = False):
        """대화 턴 추가"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'current_issue': None,
                'tried_solutions': [],
                'last_suggestion': None,
                'last_query': None,  # ✅ 추가: 마지막 질문 저장
                'created_at': datetime.now()
            }
        
        self.sessions[session_id]['history'].append({
            'timestamp': datetime.now(),
            'user_query': user_query,
            'bot_response': bot_response,
            'suggested_action': suggested_action,
            'faq_ids': faq_ids or [],
            'from_cache': from_cache
        })
        
        if suggested_action:
            self.sessions[session_id]['last_suggestion'] = suggested_action
            if suggested_action not in self.sessions[session_id]['tried_solutions']:
                self.sessions[session_id]['tried_solutions'].append(suggested_action)
        
        # ✅ 마지막 질문 저장
        self.sessions[session_id]['last_query'] = user_query
        
        if not self.sessions[session_id]['current_issue']:
            self.sessions[session_id]['current_issue'] = self._extract_issue(user_query)
    
    def _extract_issue(self, query: str) -> str:
        """현재 문제 추출"""
        issues = {
            '로그인': 'login_issue',
            '인터넷': 'internet_issue',
            '와이파이': 'wifi_issue',
            '앱': 'app_issue',
            '느림': 'slow_issue',
            '청구': 'billing_issue',
            '주문': 'order_issue'
        }
        
        for keyword, issue in issues.items():
            if keyword in query:
                return issue
        return 'general_issue'
    
    def resolve_references(self, session_id: str, query: str) -> str:
        """
        지시 대명사 해결 - 개선 버전
        
        "그거 했는데도 안 돼요" → "로그인이 안 돼요" (원래 질문으로 되돌림)
        """
        if session_id not in self.sessions:
            return query
        
        context = self.sessions[session_id]
        
        # ✅ "그거/이거/안돼요" 같은 참조어 감지
        has_reference = any(ref in query for ref in ['그거', '그것', '이거', '이것', '안돼', '안 돼'])
        
        if has_reference and context.get('last_query'):
            # ✅ 원래 질문으로 되돌림 (제안사항 추가는 맥락 프롬프트에서)
            resolved = context['last_query']
            
            # 단, "다시" 또는 "여전히" 같은 키워드 추가
            if '다시' in query or '여전히' in query or '계속' in query:
                resolved = f"{resolved} (다시 시도해도 안됨)"
            
            logger.info(f"[맥락 해결] '{query}' → '{resolved}'")
            return resolved
        
        # ✅ 기존 로직 (단어 치환)
        if context.get('last_suggestion'):
            references = {
                '그거': context['last_suggestion'],
                '그것': context['last_suggestion'],
                '이거': context['last_suggestion'],
                '이것': context['last_suggestion'],
            }
            
            resolved = query
            for ref, actual in references.items():
                if ref in query:
                    resolved = resolved.replace(ref, actual)
                    if actual not in context['tried_solutions']:
                        context['tried_solutions'].append(actual)
            
            if resolved != query:
                logger.info(f"[맥락 해결] '{query}' → '{resolved}'")
                return resolved
        
        return query
    
    def build_context_prompt(self, session_id: str) -> str:
        """대화 맥락을 프롬프트로 변환 - 강화 버전"""
        if session_id not in self.sessions:
            return ""
        
        context = self.sessions[session_id]
        if not context['tried_solutions']:
            return ""
        
        prompt = "\n[이전 대화 맥락]\n"
        prompt += f"- 현재 문제: {context['current_issue']}\n"
        
        # 문제 명확화
        if context['current_issue'] == 'login_issue':
            prompt += "  📌 로그인 자체가 안되는 문제입니다 (자동 로그인 문제 아님!)\n"
        
        prompt += f"- 고객이 이미 시도한 방법:\n"
        for i, solution in enumerate(context['tried_solutions'], 1):
            prompt += f"  {i}. {solution}\n"
        
        prompt += "\n⚠️ 중요: 위 방법들은 이미 시도했으므로 **절대 다시 제안하지 마세요**.\n"
        prompt += "⚠️ 완전히 다른 해결책을 제시해야 합니다.\n"
        prompt += "⚠️ 유사한 방법도 안 됩니다 (예: 쿠키 삭제를 했으면, 캐시 삭제도 이미 했을 가능성 높음).\n\n"
        
        return prompt


# ==================== Agent (재시도 로직) ====================

class LLMAgent:
    """LLM 호출을 담당하는 Agent"""
    
    def __init__(self, api_key: str = None, max_retries: int = 3):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_retries = max_retries
        self.client = None
        
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("  ✅ LLM Agent 초기화 완료")
            except Exception as e:
                logger.error(f"  ❌ LLM Agent 초기화 실패: {e}")
    
    def generate_with_retry(self, prompt: str, system_prompt: str = None, temperature: float = 0.7, max_tokens: int = 500) -> str:
        """재시도 로직이 있는 LLM 호출"""
        if not self.client:
            raise Exception("OpenAI 클라이언트가 초기화되지 않았습니다")
        
        system_prompt = system_prompt or self._get_default_system_prompt()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"  🤖 LLM 호출 시도 {attempt}/{self.max_retries}")
                
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                answer = response.choices[0].message.content.strip()
                logger.info(f"  ✅ LLM 호출 성공 (길이: {len(answer)}자)")
                
                return answer
                
            except Exception as e:
                logger.warning(f"  ⚠️  LLM 호출 실패 (시도 {attempt}): {e}")
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"  ⏳ {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"  ❌ LLM 호출 최종 실패")
                    raise Exception(f"LLM 호출 실패: {e}")
    
    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트 - 강화 버전"""
        return """당신은 친절하고 전문적인 고객 지원 AI입니다.

답변 규칙:
1. **최우선**: 고객이 이미 시도한 방법은 절대 다시 제안하지 마세요
2. 고객의 정확한 문제를 파악하세요
   - "로그인이 안됨" ≠ "자동 로그인 문제"
   - "결제창이 안 뜸" ≠ "결제 완료 안됨"
3. 단계별로 명확하게 설명하세요 (1, 2, 3...)
4. 기술 용어는 쉽게 풀어서 설명하세요
5. 필요시 주의사항을 추가하세요
6. 문제가 계속되면 고객센터 안내를 추가하세요
7. 존댓말을 사용하세요

절대 하지 말아야 할 것:
- 이미 시도한 방법을 다시 제안하기
- 유사한 방법도 안 됨 (쿠키 삭제 했으면 캐시 삭제도 했을 것)
- FAQ에 있어도, 이미 시도했으면 절대 언급 금지
- 문제를 잘못 이해하기 (자동 로그인 vs 일반 로그인)"""


# ==================== RAG + 캐시 지식 서비스 ====================

class CachedRAGKnowledgeService:
    """
    캐시 시스템이 추가된 RAG
    
    워크플로우:
    1. 캐시 확인 → 있으면 즉시 반환 (LLM 호출 없음)
    2. 없으면 RAG 프로세스 실행
    3. 답변 생성 후 캐시에 저장 (pending 상태)
    4. 사용자 피드백 받으면 캐시 업데이트
    """
    
    def __init__(self, 
                 csv_path: str = "backend/data/faq_database.csv",
                 cache_file: str = "backend/data/answer_cache.json",
                 model_name: str = "jhgan/ko-sroberta-multitask",
                 enable_conversation: bool = True,
                 enable_cache: bool = True,
                 api_key: str = None):
        
        logger.info("=" * 60)
        logger.info("B파트: 캐시 + RAG 시스템 초기화")
        logger.info("=" * 60)
        
        self.enable_cache = enable_cache
        self.enable_conversation = enable_conversation
        
        if enable_cache:
            self.cache = AnswerCache(cache_file)
        else:
            self.cache = None
        
        if enable_conversation:
            self.conversation = ConversationManager()
            logger.info("  ✅ 대화 맥락 관리 활성화")
        else:
            self.conversation = None
        
        self.llm_agent = LLMAgent(api_key=api_key, max_retries=3)
        
        logger.info(f"임베딩 모델 로드: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"  ✅ 임베딩 차원: {self.dimension}")
        
        self.faq_df = self._load_csv(csv_path)
        self.index = self._build_index()
        
        logger.info("✅ 캐시 + RAG 시스템 초기화 완료\n")
    
    def _load_csv(self, csv_path) -> pd.DataFrame:
        """CSV 로드 - 여러 경로 탐색 + 중복 제거"""
        base_dir = Path(__file__).parent.parent
        
        search_paths = [
            Path(csv_path),
            base_dir / "data" / "faq_database.csv",
            Path(os.getcwd()) / "backend" / "data" / "faq_database.csv",
            Path(os.getcwd()) / "data" / "faq_database.csv"
        ]
        
        csv_file = None
        for path in search_paths:
            if path.exists():
                csv_file = path
                break
        
        if not csv_file:
            raise FileNotFoundError(
                f"FAQ 파일 없음: {csv_path}\n"
                f"검색한 경로: {[str(p) for p in search_paths]}"
            )
        
        df = pd.read_csv(csv_file, encoding='utf-8')
        
        # 중복 ID 제거
        original_len = len(df)
        df = df.drop_duplicates(subset=['id'], keep='first')
        
        if len(df) < original_len:
            logger.warning(f"  ⚠️  중복 FAQ 제거: {original_len}개 → {len(df)}개")
        
        logger.info(f"  ✅ CSV 로드: {len(df)}개 FAQ")
        
        required = ['id', 'category', 'question', 'answer']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")
        
        return df
    
    def _build_index(self):
        """FAISS 인덱스 생성"""
        logger.info("FAISS 인덱스 생성 중...")
        
        texts = []
        for idx, row in self.faq_df.iterrows():
            question = str(row['question']) if pd.notna(row['question']) else ""
            text = question
            
            if 'keywords' in self.faq_df.columns and pd.notna(row['keywords']):
                text += " " + str(row['keywords']).replace(',', ' ')
            
            texts.append(text)
        
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        faiss.normalize_L2(embeddings)
        
        index = faiss.IndexFlatIP(self.dimension)
        index.add(embeddings)
        
        logger.info(f"  ✅ FAISS 인덱스: {index.ntotal}개 벡터")
        return index
    
    # ✅ agent.py 호환용 - str 반환
    def search_knowledge(self, query: str, category: str = None, session_id: str = None) -> str:
        """agent.py 호환용 메서드 - 문자열 반환"""
        result = self._search_knowledge_internal(query, category, session_id)
        return result.get('answer', '죄송합니다. 현재 답변을 생성할 수 없습니다.')

    # ✅ 실제 RAG 로직 - Dict 반환
    def _search_knowledge_internal(self, query: str, category: str = None, session_id: str = None) -> Dict:
        """실제 RAG 처리 로직"""
        original_query = query
        
        logger.info(f"\n{'='*60}")
        logger.info(f"검색 시작: '{query}'")
        logger.info(f"{'='*60}")
        
        # Step 0: 캐시 확인 (원래 질문으로)
        if self.enable_cache and self.cache:
            cached_answer = self.cache.get(original_query, category)
            
            if cached_answer:
                self.cache.increment_hit_count(original_query, category)
                logger.info("  💾 캐시에서 답변 반환 (LLM 호출 없음)")
                
                if self.conversation and session_id:
                    self.conversation.add_turn(
                        session_id=session_id,
                        user_query=original_query,
                        bot_response=cached_answer['answer'],
                        from_cache=True
                    )
                
                return {
                    "answer": cached_answer['answer'],
                    "confidence": 1.0,
                    "from_cache": True,
                    "cache_verified": cached_answer.get('verified', False),
                    "cache_hit_count": cached_answer.get('hit_count', 0),
                    "used_llm": False
                }
        
        # Step 1: 대화 맥락 해결
        if self.conversation and session_id:
            resolved_query = self.conversation.resolve_references(session_id, query)
            if resolved_query != query:
                logger.info(f"  🔄 맥락 해결됨: '{query}' → '{resolved_query}'")
                query = resolved_query
        
        # Step 2: FAQ 검색
        results = self._search_faq(query, category, top_k=3)
        
        # Step 3: 검색 결과 없어도 LLM 호출
        if not results:
            logger.warning("  ⚠️  FAQ 검색 결과 없음 - 일반 지식으로 답변")
            retrieved_context = "[FAQ 검색 결과 없음]\n일반적인 쇼핑몰 고객지원 지식을 바탕으로 친절하게 답변해주세요."
            best_score = 0.0
        else:
            retrieved_context = self._build_retrieved_context(results)
            best_score = results[0]['similarity_score']
            logger.info(f"  ✅ FAQ 검색 완료 (Top 유사도: {best_score:.2f})")
        
        # Step 4: 프롬프트 구성
        conversation_context = ""
        if self.conversation and session_id:
            conversation_context = self.conversation.build_context_prompt(session_id)
        
        final_prompt = self._chain_prompts(query, retrieved_context, conversation_context)
        
        # Step 5: LLM 호출
        try:
            logger.info("[Generation] LLM 답변 생성")
            answer = self.llm_agent.generate_with_retry(prompt=final_prompt)
            
            # 캐시에 저장 (원래 질문으로)
            if self.enable_cache and self.cache:
                self.cache.add(
                    query=original_query,
                    answer=answer,
                    category=category,
                    verified=False,
                    metadata={
                        'faq_ids': [r['faq_id'] for r in results] if results else [],
                        'confidence': best_score
                    }
                )
            
            # 대화 기록
            suggested_action = self._extract_first_action(answer)
            if self.conversation and session_id:
                self.conversation.add_turn(
                    session_id=session_id,
                    user_query=original_query,
                    bot_response=answer,
                    suggested_action=suggested_action,
                    faq_ids=[r['faq_id'] for r in results] if results else [],
                    from_cache=False
                )
            
            return {
                "answer": answer,
                "confidence": best_score,
                "from_cache": False,
                "used_llm": True,
                "matched_faq_ids": [r['faq_id'] for r in results] if results else [],
                "context_used": original_query != query,
                "pending_verification": True
            }
            
        except Exception as e:
            logger.error(f"❌ LLM 생성 실패: {e}")
            
            # LLM 실패 시 fallback
            if results:
                return {
                    "answer": results[0]['answer'],
                    "confidence": best_score,
                    "error": str(e)
                }
            else:
                return {
                    "answer": "죄송합니다. 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요.",
                    "confidence": 0.0,
                    "error": str(e)
                }
    
    def submit_feedback(self, query: str, category: str = None, is_helpful: bool = True, feedback_score: int = 5, reason: str = None):
        """사용자 피드백 제출"""
        if not self.enable_cache or not self.cache:
            logger.warning("캐시가 비활성화되어 있습니다")
            return
        
        if is_helpful:
            self.cache.verify(query, category, feedback_score)
        else:
            self.cache.reject(query, category, reason)
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계 조회"""
        if not self.enable_cache or not self.cache:
            return {'cache_enabled': False}
        
        stats = self.cache.get_stats()
        stats['cache_enabled'] = True
        return stats
    
    def _search_faq(self, query: str, category: str = None, top_k: int = 3) -> List[Dict]:
        """FAQ 검색"""
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        search_k = min(top_k * 5, len(self.faq_df))
        scores, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score < 0.1:
                continue
            
            faq_row = self.faq_df.iloc[idx]
            
            if category and faq_row['category'] != category:
                if score < 0.3:
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
    
    def _build_retrieved_context(self, results: List[Dict]) -> str:
        """검색 결과를 컨텍스트로 구성"""
        if not results:
            return ""
        
        context = "[검색된 관련 FAQ]\n\n"
        
        for i, faq in enumerate(results, 1):
            context += f"FAQ {i} (유사도: {faq['similarity_score']:.2f}):\n"
            context += f"질문: {faq['question']}\n"
            context += f"답변: {faq['answer']}\n\n"
        
        return context
    
    def _chain_prompts(self, user_query: str, retrieved_context: str, conversation_context: str) -> str:
        """프롬프트 체인"""
        prompt = ""
        
        if retrieved_context:
            prompt += retrieved_context
            prompt += "---\n\n"
        
        if conversation_context:
            prompt += conversation_context
            prompt += "---\n\n"
        
        prompt += f"[고객 질문]\n{user_query}\n\n"
        prompt += "[지시사항]\n"
        prompt += "위의 FAQ와 대화 맥락을 참고하여 답변해주세요.\n"
        
        return prompt
    
    def _extract_first_action(self, answer: str) -> Optional[str]:
        """첫 번째 조치 추출"""
        match = re.search(r'1\.\s*([^\n]+)', answer)
        if match:
            action = match.group(1).strip()
            action = re.sub(r'\([^)]*\)', '', action).strip()
            return action[:50]
        return None


# 편의를 위한 alias
KnowledgeService = CachedRAGKnowledgeService