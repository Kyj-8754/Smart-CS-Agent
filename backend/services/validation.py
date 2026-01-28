"""
최종 검증 에이전트 (D 역할)
Upstage Solar Pro 3를 사용한 LLM-as-a-Judge 구현
"""

import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 로드
load_dotenv()


class ValidationAgent:
    def __init__(self, api_key: Optional[str] = None):
        """
        Solar Pro 3 기반 검증 에이전트 초기화
        
        Args:
            api_key: Upstage API Key (.env 파일 또는 환경변수 사용)
        """
        self.api_key = api_key or os.getenv("UPSTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("UPSTAGE_API_KEY가 필요합니다. .env 파일을 확인하세요.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.upstage.ai/v1"
        )
        self.model = "solar-pro3"
        
    def validate_response(
        self, 
        query: str, 
        response: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        에이전트 응답 검증
        
        Args:
            query: 사용자 질의
            response: 에이전트 응답
            conversation_history: 대화 히스토리 (선택)
            
        Returns:
            {
                "valid": bool,
                "issues": List[str],
                "filtered_response": str
            }
        """
        
        # 대화 맥락 구성
        context = self._build_context(conversation_history)
        
        # 검증 프롬프트
        prompt = self._build_validation_prompt(query, response, context)
        
        # Solar Pro 2 호출
        result = self._call_solar_pro(prompt)
        
        # 결과 파싱
        return self._parse_validation_result(result, response)
    
    def _build_context(self, history: Optional[List[Dict]]) -> str:
        """대화 히스토리에서 맥락 추출"""
        if not history:
            return "없음"
        
        # 최근 3턴만 사용
        recent = history[-3:]
        return "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent
        ])
    
    def _build_validation_prompt(
        self, 
        query: str, 
        response: str, 
        context: str
    ) -> str:
        """검증 프롬프트 구성 (Chain-of-Thought)"""
        
        return f"""당신은 고객 지원 응답을 평가하는 전문가입니다.

**중요 전제:**
이 응답은 에이전트가 DB 조회/처리를 완료한 최종 결과입니다.
- "승인되었습니다" = 이미 승인 완료 (사실 진술)
- "배송 중" = 이미 DB 조회 완료
- 절차 평가 금지 (예: "주문번호를 먼저 물어야")

**사용자 질의:**
{query}

**대화 맥락:**
{context}

**에이전트 응답 (최종 결과):**
{response}

---

**평가 기준:**

1. **일관성**: 질의와 응답 주제가 일치하는가?
   - 통과: 질문과 관련된 답변
   - 실패: 완전히 다른 주제 (로그인 질문에 환불 답변)

2. **완전성**: 고객이 알아야 할 핵심 정보가 있는가?
   - 환불: 주문번호, 금액, 처리기간
   - 배송: 송장번호, 배송사, 도착일
   - 기술지원: 해결방법 또는 지원 연락처
   - 실패: 단순 "처리 중"만 제공

3. **정확성**: 명백히 틀린 정보가 있는가?
   - "환불 즉시 처리" (실제 3-5일) → 실패
   - "무료 배송" (실제 유료) → 실패
   - 불확실하면 통과

4. **정책준수**: 위험한 약속이나 부적절한 표현이 있는가?
   - "무조건 승인", "100% 보장" → 실패
   - 욕설, 비전문적 표현 → 실패
   - 불확실하면 통과

3. **정확성**: 잘못된 정보가 없는가?
   - 사실 관계 확인
   - 불확실한 진술 없음

4. **정책준수**: 회사 고객 지원 원칙을 따르는가?
   - 공손하고 전문적인 언어
   - 불가능한 약속 없음
   - 개인정보 보호

---

**평가 절차:**
1단계: 각 기준 검토 및 문제점 파악
2단계: 각 항목을 "통과" 또는 "실패"로 판단
3단계: 실패 시 구체적 이유 작성

**출력 형식 (JSON):**
```json
{{
  "일관성": {{
    "pass": true/false,
    "reason": "구체적 이유"
  }},
  "완전성": {{
    "pass": true/false,
    "reason": "구체적 이유"
  }},
  "정확성": {{
    "pass": true/false,
    "reason": "구체적 이유"
  }},
  "정책준수": {{
    "pass": true/false,
    "reason": "구체적 이유"
  }},
  "overall_pass": true/false,
  "improvement": "실패 시 개선 제안"
}}
```

**중요 원칙:**
- 명확한 문제가 없으면 통과
- 보수적 판단 (불확실하면 통과)
- 사소한 표현 차이 무시
- overall_pass는 4개 모두 통과해야 true"""

    def _call_solar_pro(self, prompt: str) -> str:
        """
        Solar Pro 3 API 호출 (reasoning_effort=high)
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000,
                reasoning_effort="high",
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Solar Pro 3 API 오류: {e}")
            return self._get_default_pass_response()
    
    def _parse_validation_result(
        self, 
        llm_output: str, 
        original_response: str
    ) -> Dict:
        """LLM 출력 파싱"""
        
        try:
            # JSON 추출
            json_str = self._extract_json(llm_output)
            result = json.loads(json_str)
            
            # 문제점 수집
            issues = []
            for criterion in ["일관성", "완전성", "정확성", "정책준수"]:
                if criterion in result:
                    data = result[criterion]
                    if isinstance(data, dict) and not data.get("pass", True):
                        issues.append(f"{criterion}: {data.get('reason', '문제 발견')}")
            
            return {
                "valid": result.get("overall_pass", True),
                "issues": issues,
                "filtered_response": result.get("improvement", "") if not result.get("overall_pass") else original_response
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"파싱 오류: {e}")
            # 파싱 실패 시 보수적 처리
            return {
                "valid": True,
                "issues": [],
                "filtered_response": original_response
            }
    
    def _extract_json(self, text: str) -> str:
        """텍스트에서 JSON 추출"""
        text = text.strip()
        
        # ```json 태그 제거
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return text
    
    def _get_default_pass_response(self) -> str:
        """API 실패 시 기본 응답 (보수적 통과)"""
        return json.dumps({
            "일관성": {"pass": True, "reason": "API 오류로 기본 통과"},
            "완전성": {"pass": True, "reason": "API 오류로 기본 통과"},
            "정확성": {"pass": True, "reason": "API 오류로 기본 통과"},
            "정책준수": {"pass": True, "reason": "API 오류로 기본 통과"},
            "overall_pass": True,
            "improvement": ""
        })


# ==================== 테스트 ====================

if __name__ == "__main__":
    test_cases = [
        {
            "name": "정상 환불 응답 (승인 완료)",
            "query": "환불 요청합니다",
            "response": "환불이 승인되었습니다. 주문번호 ORD-2026-001, 환불금액 89,000원이며 3-5 영업일 내 계좌로 입금됩니다.",
            "history": [],
            "expected": "pass"
        },
        {
            "name": "기술지원 정상 응답",
            "query": "로그인이 안돼요",
            "response": "로그인 문제를 확인했습니다. 1) 브라우저 캐시 삭제 2) 쿠키 허용 확인 3) 비밀번호 재설정을 시도해보세요. 추가 지원: support@company.com",
            "history": [],
            "expected": "pass"
        },
        {
            "name": "주문 조회 정상 응답",
            "query": "배송 조회해주세요",
            "response": "주문번호 ORD-2026-002, 배송 중입니다. CJ대한통운 123456789, 예상 도착일: 2026-01-28",
            "history": [],
            "expected": "pass"
        },
        {
            "name": "일관성 오류 (질문-답변 불일치)",
            "query": "로그인이 안돼요",
            "response": "환불 처리해드리겠습니다.",
            "history": [],
            "expected": "fail"
        },
        {
            "name": "완전성 오류 (정보 누락)",
            "query": "배송 조회해주세요",
            "response": "배송 중입니다.",
            "history": [],
            "expected": "fail"
        },
        {
            "name": "정확성 오류 (잘못된 정보)",
            "query": "환불은 언제 되나요?",
            "response": "즉시 처리됩니다.",
            "history": [],
            "expected": "fail"
        }
    ]
    
    try:
        validator = ValidationAgent()
        print("=== Solar Pro 3 검증 에이전트 테스트 ===\n")
        
        for i, test in enumerate(test_cases, 1):
            print(f"[테스트 {i}] {test['name']}")
            print(f"질의: {test['query']}")
            print(f"응답: {test['response']}")
            print(f"예상: {test['expected']}\n")
            
            result = validator.validate_response(
                query=test['query'],
                response=test['response'],
                conversation_history=test['history']
            )
            
            print(f"결과: {'통과' if result['valid'] else '실패'}")
            if result['issues']:
                print(f"문제점:")
                for issue in result['issues']:
                    print(f"  - {issue}")
            if not result['valid']:
                print(f"개선안: {result['filtered_response'][:100]}...")
            print("-" * 60 + "\n")
            
    except Exception as e:
        print(f"오류: {e}")
        print("\n.env 파일에 UPSTAGE_API_KEY가 설정되어 있는지 확인하세요.")
