# Smart CS Agent - Frontend (D 역할)

AI 기반 고객 지원 에이전트 시스템의 프론트엔드 UI 및 승인 시스템

**담당:** D 역할 (출력 검증 및 승인 UI)

---

## 빠른 시작

```bash
cd frontend
npm install
npm run dev
```

브라우저: http://localhost:5173

**로그인:** admin / admin123

---

## 주요 기능

### 1. 로그인 시스템
- JSON 파일 기반 인증
- localStorage 세션 관리
- 계정: admin/admin123, test/test123

### 2. 채팅 인터페이스
- 실시간 메시지 표시
- 자동 스크롤
- Enter 키 전송

### 3. 승인 다이얼로그 (핵심 기능)
- 트랜잭션 승인/취소 UI
- 구조화된 데이터 표시 (JSON 파싱)
- 모달 오버레이

### 4. 사이드바
- 사용자 정보 표시
- 숨기기/보이기 토글
- 로그아웃 기능

---

## 현재 상태

**Mock 모드**: 백엔드 없이 4개 에이전트 테스트 가능
- 기술 지원 (tech_support)
- 환불 (refund)
- 주문 관리 (order)
- 계정 관리 (account)

---

## 테스트 시나리오

### 기술 지원 에이전트
입력: "로그인이 안돼요"
결과: 일반 응답 (승인 불필요)

### 환불 에이전트
입력: "환불 요청합니다"
결과: 승인 다이얼로그 표시

데이터 표시:
- 주문번호: ORD_2026_001
- 환불금액: 89,000원
- 환불사유: 단순 변심

### 주문 관리 에이전트
입력: "주문 조회해주세요"
결과: 주문 정보 표시 (승인 불필요)

입력: "배송지 변경하고 싶어요"
결과: 승인 다이얼로그 표시

### 계정 관리 에이전트
입력: "회원 탈퇴하고 싶어요"
결과: 승인 다이얼로그 표시

데이터 표시:
- 회원ID, 가입일
- 보유포인트 (소멸 예정)
- 경고사항

---

## 디자인

### 색상 팔레트
- Primary: #1A3263 (네이비)
- Secondary: #547792 (블루그레이)
- Accent: #FAB95B (오렌지)
- Background: #E8E2DB (베이지)

### UI 특징
- 사이드바 토글 기능
- 깔끔한 모던 디자인
- 반응형 레이아웃

---

## 파일 구조

```
frontend/
├── src/
│   ├── components/
│   │   ├── Login.jsx           # 로그인
│   │   ├── Chat.jsx            # 채팅 메인
│   │   ├── Message.jsx         # 메시지
│   │   ├── ApprovalDialog.jsx  # 승인 다이얼로그
│   │   └── Sidebar.jsx         # 사이드바
│   ├── services/
│   │   ├── api.js              # Mock/실제 API
│   │   └── auth.js             # 인증 관리
│   └── styles/
│       └── colors.js           # 색상 팔레트
├── public/
│   └── users.json              # 로그인 정보
└── package.json
```

---

## 백엔드 API 연결

### 필요한 엔드포인트

**POST /chat**
```json
요청: { "query": "사용자 메시지" }
응답: {
  "message": "에이전트 응답",
  "requires_approval": false,
  "transaction_id": "...",
  "approval_message": "...",
  "transaction_data": {...},
  "metadata": {...}
}
```

**POST /approve**
```json
요청: { "transaction_id": "...", "approved": true }
응답: { "status": "success", "message": "..." }
```

### CORS 설정 필요
```python
# backend
allow_origins=["http://localhost:5173"]
```

### API 연결 방법
`src/services/api.js` 파일에서:
1. Mock 함수 주석 처리
2. 실제 API 함수 주석 해제

---

## 트러블슈팅

### "vite를 찾을 수 없습니다"
```bash
npm install
```

### 포트 충돌 (5173 사용 중)
```bash
npm run dev -- --port 3000
```

### node_modules 오류
```bash
rm -rf node_modules package-lock.json
npm install
```

---

## 완성도

- [x] 로그인 시스템
- [x] 채팅 UI
- [x] 승인 다이얼로그 (4개 에이전트)
- [x] 사이드바 토글
- [x] Mock 데이터
- [x] 실제 API 인터페이스
- [ ] 대화 기록 (미구현)
- [ ] 설정 페이지 (미구현)

---

## 개발 참고

### Mock 데이터 커스터마이징
`src/services/api.js`의 AGENT_RESPONSES 수정

### 색상 변경
`src/styles/colors.js` 파일 수정

### 새 에이전트 추가
api.js에 키워드와 응답 로직 추가

---

**구현 완료일:** 2026-01-26
**다른 역할 파일 수정:** 없음
