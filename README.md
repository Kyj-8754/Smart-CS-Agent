# 스마트 CS 상담 에이전트 (Smart CS Agent)

이 프로젝트는 RAG(검색 증강 생성) 기반의 지능형 고객 상담 자동화 시스템입니다. 
사용자의 의도를 파악하여 기술 지원, 거래 처리, 일반 대화로 분류하고 적절한 응답을 생성합니다.

## 프로젝트 구조

```text
d:\Smart-CS-Agent\
├── backend\                # FastAPI 백엔드 서버
│   ├── app.py              # 메인 애플리케이션 진입점
│   ├── router.py           # API 라우터 정의
│   ├── agent.py            # 4단계 워크플로우 오케스트레이션 에이전트
│   └── services\           # 핵심 서비스 모듈
│       ├── classification.py # 단계 A: 의도 분류 및 입력 검증
│       ├── knowledge.py      # 단계 B: 기술 지원 (FAQ/매뉴얼 검색)
│       ├── transaction.py    # 단계 C: 주문/계정 처리
│       └── validation.py     # 단계 D: 출력 검증
├── frontend\               # React (Vite) 프론트엔드
├── requirements.txt        # 백엔드 의존성 패키지 목록
└── README.md               # 프로젝트 설명 (본 파일)
```

## 시작하기

### 1단계: 백엔드 실행

Python 3.11 환경에서 다음 명령어를 실행하여 필요한 패키지를 설치하고 서버를 시작합니다.

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (backend 폴더가 있는 루트 경로에서 실행)
uvicorn backend.app:app --reload
```
서버는 `http://localhost:8000`에서 실행됩니다.

### 2단계: 프론트엔드 실행

`frontend` 디렉토리로 이동하여 의존성을 설치하고 개발 서버를 시작합니다.

```bash
cd frontend
npm install
npm run dev
```

## 워크플로우

1. **분류 및 검증**: 사용자 입력을 분석하여 기술 지원, 거래, 잡담 등으로 분류합니다.
2. **기술 지원**: 기술적 질문인 경우 지식 베이스(FAQ)를 검색하여 답변합니다.
3. **청구/주문 처리**: 계정 변경이나 주문 취소 요청 시 트랜잭션을 생성하고 승인 대기 상태로 만듭니다.
4. **검증 및 승인**: 생성된 응답을 검증하고, 중요 작업에 대해 사용자 승인을 요청합니다.
