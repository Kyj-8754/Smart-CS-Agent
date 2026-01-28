"""
knowledge.py 단독 테스트 스크립트
백엔드만으로 knowledge.py가 잘 작동하는지 확인

실행 방법:
python test_knowledge.py
"""

import os
from dotenv import load_dotenv
import sys

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "=" * 70)
print("🧪 knowledge.py 테스트 시작")
print("=" * 70)

# ==================== 1단계: Import 테스트 ====================

print("\n[1단계] 패키지 Import 테스트...")

try:
    from sentence_transformers import SentenceTransformer
    print("  ✅ sentence-transformers")
except ImportError as e:
    print(f"  ❌ sentence-transformers 없음: {e}")
    print("     설치: pip install sentence-transformers")
    sys.exit(1)

try:
    import faiss
    print("  ✅ faiss")
except ImportError as e:
    print(f"  ❌ faiss 없음: {e}")
    print("     설치: pip install faiss-cpu")
    sys.exit(1)

try:
    import pandas as pd
    print("  ✅ pandas")
except ImportError as e:
    print(f"  ❌ pandas 없음: {e}")
    print("     설치: pip install pandas")
    sys.exit(1)

try:
    from openai import OpenAI
    print("  ✅ openai")
except ImportError as e:
    print(f"  ❌ openai 없음: {e}")
    print("     설치: pip install openai")
    sys.exit(1)

print("✅ 모든 패키지 Import 성공!")

# ==================== 2단계: OpenAI API 키 확인 ====================

print("\n[2단계] OpenAI API 키 확인...")
load_dotenv() 

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"  ✅ API 키 발견: {api_key[:10]}...{api_key[-4:]}")
else:
    print("  ⚠️  OPENAI_API_KEY 환경변수 없음")
    print("     설정: export OPENAI_API_KEY='sk-...'")
    print("     계속 진행하지만 LLM 호출은 실패할 수 있습니다.")

# ==================== 3단계: FAQ 파일 확인 ====================

print("\n[3단계] FAQ 파일 확인...")

faq_paths = [
    "data/faq_database.csv",
    "faq_database.csv",
    "../data/faq_database.csv"
]

faq_file = None
for path in faq_paths:
    if os.path.exists(path):
        faq_file = path
        print(f"  ✅ FAQ 파일 발견: {path}")
        break

if not faq_file:
    print("  ❌ FAQ 파일 없음")
    print("     다음 경로 중 하나에 배치하세요:")
    for path in faq_paths:
        print(f"     - {path}")
    
    # 테스트용 FAQ 생성
    print("\n  📝 테스트용 FAQ 파일 생성 중...")
    os.makedirs("data", exist_ok=True)
    faq_file = "data/faq_database.csv"
    
    with open(faq_file, "w", encoding="utf-8") as f:
        f.write("id,category,question,answer,keywords\n")
        f.write('faq_001,tech_support,로그인이 안 돼요,"비밀번호를 재설정하세요",로그인,비밀번호\n')
        f.write('faq_002,tech_support,인터넷이 안 돼요,"라우터를 재부팅하세요",인터넷,연결\n')
        f.write('faq_003,billing_support,청구서 확인,"마이페이지에서 확인하세요",청구,요금\n')
    
    print(f"  ✅ 테스트용 FAQ 생성: {faq_file}")

# ==================== 4단계: KnowledgeService 초기화 ====================

print("\n[4단계] KnowledgeService 초기화...")

try:
    # services/knowledge.py 또는 knowledge.py import 시도
    try:
        from backend.services.knowledge import KnowledgeService
        print("  ✅ services/knowledge.py에서 import")
    except ImportError:
        from backend.services.knowledge import KnowledgeService
        print("  ✅ knowledge.py에서 import")
    
    service = KnowledgeService(
        csv_path=faq_file,
        cache_file="data/test_cache.json",
        enable_conversation=True,
        enable_cache=True,
        api_key=api_key
    )
    
    print("  ✅ KnowledgeService 초기화 성공!")
    
except Exception as e:
    print(f"  ❌ 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==================== 5단계: 검색 테스트 (캐시 미스) ====================

print("\n[5단계] 검색 테스트 (첫 번째 질문 - 캐시 미스)...")

session_id = "test_user_001"
query = "로그인이 안 돼요"

try:
    result = service.search_knowledge(
        query=query,
        category="tech_support",
        session_id=session_id
    )
    
    print(f"  ✅ 검색 성공!")
    print(f"     답변: {result[:100]}..." if len(result) > 100 else f"     답변: {result}")
    
except Exception as e:
    print(f"  ❌ 검색 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ==================== 6단계: 피드백 테스트 ====================

print("\n[6단계] 피드백 테스트 (긍정 피드백)...")

try:
    service.submit_feedback(
        query=query,
        category="tech_support",
        is_helpful=True,
        feedback_score=5
    )
    
    print("  ✅ 피드백 제출 성공!")
    
except Exception as e:
    print(f"  ❌ 피드백 실패: {e}")
    import traceback
    traceback.print_exc()

# ==================== 7단계: 캐시 테스트 (캐시 히트) ====================

print("\n[7단계] 캐시 테스트 (같은 질문 다시 - 캐시 히트)...")

try:
    result2 = service.search_knowledge(
        query=query,
        category="tech_support",
        session_id=session_id
    )
    
    print(f"  ✅ 캐시 검색 성공!")
    print(f"     답변: {result2[:100]}..." if len(result2) > 100 else f"     답변: {result2}")
    
except Exception as e:
    print(f"  ❌ 캐시 검색 실패: {e}")
    import traceback
    traceback.print_exc()

# ==================== 8단계: 대화 맥락 테스트 ====================

print("\n[8단계] 대화 맥락 테스트 ('그거 했어요')...")

query2 = "그거 했는데도 안 돼요"

try:
    result3 = service.search_knowledge(
        query=query2,
        category="tech_support",
        session_id=session_id
    )
    
    print(f"  ✅ 대화 맥락 처리 성공!")
    print(f"     답변: {result3[:100]}..." if len(result3) > 100 else f"     답변: {result3}")
    
except Exception as e:
    print(f"  ❌ 대화 맥락 실패: {e}")
    import traceback
    traceback.print_exc()

# ==================== 9단계: 통계 확인 ====================

print("\n[9단계] 캐시 통계 확인...")

try:
    stats = service.get_cache_stats()
    
    print("  ✅ 통계 조회 성공!")
    print(f"     캐시 활성화: {stats.get('cache_enabled')}")
    print(f"     전체 캐시: {stats.get('total_cached')}개")
    print(f"     검증됨: {stats.get('verified')}개")
    print(f"     대기중: {stats.get('pending')}개")
    print(f"     총 히트: {stats.get('total_cache_hits')}회")
    
except Exception as e:
    print(f"  ❌ 통계 조회 실패: {e}")
    import traceback
    traceback.print_exc()

# ==================== 최종 결과 ====================

print("\n" + "=" * 70)
print("🎉 모든 테스트 완료!")
print("=" * 70)

print("\n✅ 성공한 테스트:")
print("  1. 패키지 Import")
print("  2. OpenAI API 키 확인")
print("  3. FAQ 파일 로드")
print("  4. KnowledgeService 초기화")
print("  5. 검색 (캐시 미스)")
print("  6. 피드백 제출")
print("  7. 검색 (캐시 히트)")
print("  8. 대화 맥락 처리")
print("  9. 통계 조회")

print("\n📁 생성된 파일:")
print(f"  - FAQ: {faq_file}")
print(f"  - 캐시: data/test_cache.json")

print("\n🚀 다음 단계:")
print("  1. agent.py 수정")
print("  2. router.py 실행: python router.py")
print("  3. http://localhost:8000/docs 접속")

print("\n" + "=" * 70)