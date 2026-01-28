# Conda 가상 환경 설정 가이드

## 1. Anaconda Prompt 열기
Windows 시작 메뉴에서 "Anaconda Prompt" 검색 후 실행

## 2. 프로젝트 디렉토리로 이동
```bash
cd C:\A_AI_POC_WS\Smart-CS-Agent
```

## 3. 가상 환경 생성
```bash
conda create -n smart-cs-agent python=3.11 -y
```

## 4. 가상 환경 활성화
```bash
conda activate smart-cs-agent
```

## 5. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

## 6. 검증 스크립트 실행
```bash
python verify_scenarios.py
```

## 7. 서버 실행 (선택사항)
```bash
uvicorn backend.app:app --reload
```

---

## 참고: PowerShell에서 conda 사용하기

PowerShell에서 conda를 사용하려면 한 번만 초기화하면 됩니다:

1. Anaconda Prompt를 관리자 권한으로 실행
2. 다음 명령어 실행:
```bash
conda init powershell
```
3. PowerShell을 재시작하면 conda 명령어 사용 가능
