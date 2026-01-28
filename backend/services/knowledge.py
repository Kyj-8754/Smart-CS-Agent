import json
import os
import hashlib
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 캐시 관리자 ====================

class AnswerCache:
    def __init__(self, cache_file: str = "data/answer_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        logger.info(f"✅ 답변 캐시 초기화 ({len(self.cache)}개 저장됨)")
    
    def _load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
    
    def _get_query_hash(self, query: str, category: str = None) -> str:
        key = f"{category}:{query}" if category else query
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, query: str, category: str = None) -> Optional[Dict]:
        query_hash = self._get_query_hash(query, category)
        if query_hash in self.cache:
            item = self.cache[query_hash]
            if item.get('verified', False):
                logger.info("💾 캐시 히트! (검증된 답변)")
                return item
        return None
    
    def add(self, query: str, answer: str, category: str = None, verified: bool = False, metadata: Dict = None):
        query_hash = self._get_query_hash(query, category)
        self.cache[query_hash] = {
            'query': query,
            'answer': answer,
            'category': category,
            'verified': verified,
            'created_at': datetime.now().isoformat(),
            'hit_count': 0,
            'metadata': metadata or {}
        }
        self._save_cache()
    
    def verify(self, query: str, category: str = None):
        query_hash = self._get_query_hash(query, category)
        if query_hash in self.cache:
            self.cache[query_hash]['verified'] = True
            self.cache[query_hash]['verified_at'] = datetime.now().isoformat()
            self._save_cache()

    def reject(self, query: str, category: str = None, reason: str = None):
        query_hash = self._get_query_hash(query, category)
        if query_hash in self.cache:
            self.cache[query_hash]['verified'] = False
            self.cache[query_hash]['rejected'] = True
            self._save_cache()

    def increment_hit_count(self, query: str, category: str = None):
        query_hash = self._get_query_hash(query, category)
        if query_hash in self.cache:
            self.cache[query_hash]['hit_count'] += 1
            self._save_cache()

    def get_stats(self) -> Dict:
        total = len(self.cache)
        verified = sum(1 for item in self.cache.values() if item.get('verified'))
        return {'total_cached': total, 'verified': verified}

# ==================== 대화 맥락 관리자 ====================

class ConversationManager:
    def __init__(self):
        self.sessions = {}
    
    def add_turn(self, session_id: str, user_query: str, bot_response: str, suggested_action: str = None, from_cache: bool = False):
        if session_id not in self.sessions:
            self.sessions[session_id] = {'history': [], 'tried_solutions': [], 'last_suggestion': None}
        
        self.sessions[session_id]['history'].append({'query': user_query, 'response': bot_response, 'from_cache': from_cache})
        if suggested_action:
            self.sessions[session_id]['last_suggestion'] = suggested_action
            self.sessions[session_id]['tried_solutions'].append(suggested_action)

    def resolve_references(self, session_id: str, query: str) -> str:
        if session_id not in self.sessions or not self.sessions[session_id]['last_suggestion']:
            return query
        ref = self.sessions[session_id]['last_suggestion']
        return query.replace("그거", ref).replace("이거", ref)

    def build_context_prompt(self, session_id: str) -> str:
        if session_id not in self.sessions or not self.sessions[session_id]['tried_solutions']:
            return ""
        solutions = ", ".join(self.sessions[session_id]['tried_solutions'])
        return f"\n[이미 시도한 방법: {solutions}] ⚠️ 위 방법 외의 해결책을 제시하세요.\n"

# ==================== LLM Agent ====================

class LLMAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except:
            self.client = None

    def generate_with_retry(self, prompt: str) -> str:
        if not self.client: return "OpenAI API 키가 필요합니다."
        res = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "친절한 상담원입니다."}, {"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()

# ==================== RAG + 캐시 지식 서비스 ====================

class CachedRAGKnowledgeService:
    def __init__(self, csv_path: str, cache_file: str = "data/answer_cache.json", enable_cache: bool = True):
        self.enable_cache = enable_cache
        self.cache = AnswerCache(cache_file) if enable_cache else None
        self.conversation = ConversationManager()
        self.llm_agent = LLMAgent()
        self.model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        self.faq_df = pd.read_csv(csv_path)
        self.index = self._build_index()

    def _build_index(self):
        texts = (self.faq_df['question'] + " " + self.faq_df.get('keywords', '').fillna('')).tolist()
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index

    def _search_faq(self, query: str, category: str = None, top_k: int = 3) -> List[Dict]:
        query_emb = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)
        scores, indices = self.index.search(query_emb, min(top_k * 2, len(self.faq_df)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            row = self.faq_df.iloc[idx]
            if category and row['category'] != category: continue
            results.append({'faq_id': row['id'], 'question': row['question'], 'answer': row['answer'], 'similarity_score': float(score)})
            if len(results) >= top_k: break
        return results

    def search_knowledge(self, query: str, category: str = None, session_id: str = None) -> Dict:
        if self.enable_cache:
            cached = self.cache.get(query, category)
            if cached:
                self.cache.increment_hit_count(query, category)
                return {"answer": cached['answer'], "from_cache": True, "used_llm": False}

        resolved_query = self.conversation.resolve_references(session_id, query) if session_id else query
        faqs = self._search_faq(resolved_query, category)
        
        if not faqs: return {"answer": "죄송합니다. 관련 정보를 찾을 수 없습니다.", "confidence": 0.0}

        context = "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faqs])
        conv_prompt = self.conversation.build_context_prompt(session_id) if session_id else ""
        
        final_prompt = f"{context}\n{conv_prompt}\n질문: {resolved_query}"
        answer = self.llm_agent.generate_with_retry(final_prompt)

        if self.enable_cache:
            self.cache.add(query, answer, category)
        
        if session_id:
            self.conversation.add_turn(session_id, query, answer)

        return {"answer": answer, "from_cache": False, "used_llm": True, "confidence": faqs[0]['similarity_score']}

    def submit_feedback(self, query: str, category: str = None, is_helpful: bool = True):
        if self.cache:
            if is_helpful: self.cache.verify(query, category)
            else: self.cache.reject(query, category)

    def get_cache_stats(self):
        return self.cache.get_stats() if self.cache else {}

# 별칭
KnowledgeService = CachedRAGKnowledgeService

# ==================== 테스트 ====================

def test_cache_system():
    print("\n" + "=" * 70)
    print("캐시 시스템 테스트")
    print("=" * 70)
    
    # 본인의 실제 파일명 확인 필수 
    csv_file = "faq_database.csv" 
    if not os.path.exists(csv_file):
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("id,category,question,answer,keywords\nfaq_001,tech_support,인터넷 안됨,공유기를 껐다 켜세요,인터넷")

    service = KnowledgeService(csv_path=csv_file)
    session_id = "test_user_123"
    query = "인터넷이 안 돼요"
    
    print("\n[테스트 1] 첫 번째 요청 (캐시 미스)")
    res1 = service.search_knowledge(query, "tech_support", session_id)
    print(f"캐시 사용: {res1['from_cache']} | 답변: {res1['answer'][:50]}...")
    
    print("\n[테스트 2] 긍정 피드백 제출")
    service.submit_feedback(query, "tech_support", True)
    
    print("\n[테스트 3] 두 번째 요청 (캐시 히트)")
    res2 = service.search_knowledge(query, "tech_support", session_id)
    print(f"캐시 사용: {res2['from_cache']} | 답변: {res2['answer'][:50]}...")

if __name__ == "__main__":
    test_cache_system()