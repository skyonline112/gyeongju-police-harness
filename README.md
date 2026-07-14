# 공무원/경찰 행정 민원 답변 생성 및 법률/품질 검증 에이전트 하네스 (Civil Complaint Assistant)

본 프로젝트는 공무원 및 경찰관서에 접수되는 행정 민원에 대해 **4명의 전문 AI 에이전트 팀**이 협업하여 `입력 ➔ 처리 ➔ 검증 ➔ 출력` 파이프라인을 처리하는 **엔터프라이즈급 행정 자동화 하네스(Harness)**입니다.

단일 거대 언어 모델(LLM)의 판단 오류(Hallucination)를 방지하고, 행정 서식의 준수와 개인정보 보호 요건을 완벽히 만족하기 위해 **실시간 웹 검색(Dynamic Web Search)** 및 **병렬 검수진 합의체(Consensus Review Consortium)** 아키텍처를 도입했습니다.

---

## 1. 아키텍처 설계 및 구성 목적

1. **실시간 웹 검색 (Dynamic Web Search)**: 로컬 규정 DB 검색뿐만 아니라, 최신 인사혁신처/경찰청 행정 지침이나 개정 법령을 실시간 웹 검색 도구로 동적 수집하여 정보의 stale(시차) 문제를 해결합니다.
2. **병렬 검수 및 합의(Consensus) 아키텍처**: 작성된 답변서 초안을 3인의 전문 검수진(법률, 개인정보, 대민 소통)이 동시에 병렬로 교차 심사합니다. 단 한 명이라도 결함을 지적(`REJECTED`)할 경우, 통합 피드백을 동반해 일괄 반려하는 엄격한 행정 승인 알고리즘을 따릅니다.
3. **개인정보 유출 방지 및 마스킹**: 주민등록번호, 차량번호, 상대방 실명 등 고유 식별 정보가 공문서에 무단 노출되는 것을 완벽히 탐지하고 차단합니다.
4. **표준 공문서 톤앤매너**: 대한민국 정부 표준 공문 서식 및 친절한 두괄식 결론 작성법을 준수합니다.

---

## 2. 에이전트 팀 구성 및 역할

- **Classifier (분류 에이전트)**: 접수된 민원을 인사/채용, 복무/징계, 보수/여비/수당, 일반행정/기타 중 적절한 카테고리로 정밀 분류합니다.
- **Searcher (법령/웹 검색 에이전트)**: 카테고리에 기반하여 로컬 DB 및 실시간 웹 검색(Tavily/Google API)을 가동해 근거 법률 조항(조, 항, 호) 및 유관 판례를 수집합니다.
- **Drafter (답변 집필 에이전트)**: 수집된 법령 근거를 바탕으로 정중하고 격식 있는 톤으로 답변서 초안을 작성합니다. 반려 피드백이 전송되면 이를 즉시 분석하여 개정본을 작성합니다.
- **Reviewer Consortium (병렬 검수 에이전트 팀)**:
  1. **Legal Auditor (법률 검수관)**: 인용된 법령이 조작되거나 왜곡되지 않았는지 정합성 검사.
  2. **Privacy Inspector (개인정보 검수관)**: 제3자 개인 식별 정보 및 민감 정보의 유출 여부 검사.
  3. **PR Officer (대민 소통 검수관)**: 어투가 친절한지, 결론 두괄식 및 필수 안내 수령 절차가 반영되었는지 가독성 검사.

---

## 3. 전체 아키텍처 및 데이터 흐름

```mermaid
graph TD
    Input[시민 민원 신청서] --> Classifier[Classifier Agent]
    
    subgraph Knowledge Acquisition (지식 획득)
        Classifier -->|분류 결과 송신| Searcher[Searcher Agent]
        Searcher -->|1차| LocalDB[(로컬 규정 DB)]
        Searcher -->|2차| WebSearch[Dynamic Web Search: 최신 법령/판례 수집]
    end
    
    Searcher -->|구조화된 법률 근거| Drafter[Drafter Agent: 답변서 기획/집필]
    Drafter -->|답변 초안 전송| ParallelGate{병렬 검수 게이트}
    
    subgraph Reviewer Consortium (병렬 합의 검수단)
        ParallelGate --> Reviewer1[Legal Auditor: 법적 무오류성 검토]
        ParallelGate --> Reviewer2[Privacy Inspector: 개인정보 노출 필터링]
        ParallelGate --> Reviewer3[PR Officer: 가독성 & 공익성 평가]
    end
    
    Reviewer1 --> Consensus{Consensus Engine}
    Reviewer2 --> Consensus
    Reviewer3 --> Consensus
    
    Consensus -->|REJECTED: 통합 피드백 피스팅| Drafter
    Consensus -->|APPROVED: 전원 합의 통과| Output[최종 정보공개 결정통지서 출력]
```

---

## 4. 디렉토리 구조

```text
8회차 과제/
├── README.md                           # 과제 종합 설명서 (본 파일)
├── run_harness.py                      # 에이전트 실행기 (Single/Batch 모드)
├── laws_db.py                          # 공무원/경찰 관련 법령 데이터베이스
├── index.html                          # 인터랙티브 비주얼 웹 대시보드
├── .env.example                        # 환경 변수 설정 양식
├── _workspace/                         # 에이전트 협업으로 도출된 마크다운 산출물
│   ├── 00_input.md                     # 입력 민원
│   ├── 01_classification.md           # 분류 결과
│   ├── 02_laws_search.md              # 규정 검색 결과
│   ├── 03_draft_reply.md              # 1차 초안 (오류 발생본)
│   ├── 04_review_report.md            # 반려 및 수정 가이드
│   └── 05_final_notice.md             # [최종] 최종 승인 답변서
└── .claude/                            # 에이전트 프롬프트 및 스킬 정의
    ├── CLAUDE.md                       # 하네스 메타 정보
    ├── agents/
    │   ├── classifier.md               # 분류 에이전트 정의
    │   ├── searcher.md                 # 검색 에이전트 정의
    │   ├── drafter.md                  # 작성 에이전트 정의
    │   └── reviewer.md                 # 검수 에이전트 정의
    └── skills/
        └── complaint-assistant/
            └── skill.md                # 오케스트레이터 및 합의 스킬
```

---

## 5. 사용 방법 및 실행 예시

### 1) 환경 설정 및 가상 실행 지원
의존 라이브러리를 설치하고 API 키를 설정합니다. **API 키가 없거나 미설정된 경우, 시스템은 자동으로 [가상 시뮬레이션 모드]로 전환되어 채점자가 즉시 에이전트 실행 로그를 관찰할 수 있도록 지원합니다.**

```bash
# 의존 패키지 설치
pip install pandas openpyxl openai python-dotenv

# API Key 설정 (.env 생성)
copy .env.example .env
```

### 2) 터미널 구동 및 실시간 모니터링
```bash
python run_harness.py
```
- **모드 1 (Single Mode)**: 예시 경찰 민원(CCTV 정보공개청구 건)에 대해 실시간으로 에이전트들이 협업하여 답변을 짓고, 1차 반려를 거쳐 2차 완성본으로 최종 승인되는 전 과정을 순회하여 결과를 `_workspace/` 폴더에 마크다운으로 실시간 갱신합니다.
- **모드 2 (Batch Mode)**: `complaints_input.xlsx` 파일을 로드하여 수십 건의 대량 민원을 일괄 에이전트 파이프라인으로 처리한 뒤, 답변 초안이 완성된 최종 `complaints_result.xlsx` 엑셀 파일을 도출합니다. (입력용 엑셀 파일이 존재하지 않는 경우 자동으로 모사 엑셀 데이터를 생성합니다.)

### 3) 비주얼 웹 대시보드
프로젝트 폴더 내의 `index.html` 파일을 웹 브라우저로 열어 실행합니다.
- 로컬 `file://` 환경에서도 CORS 오류 없이 에이전트별 캐릭터 카드와 협업 마크다운 산출물이 매끄러운 탭 애니메이션으로 렌더링되어 한눈에 동작 과정을 볼 수 있습니다.

---

## 6. 핵심 에이전트 협업 실행 예시 (경찰 CCTV 정보공개 청구)

1. **입력(00_input.md)**: 강남역 접촉사고 당사자 김철수 님이 상대 운전자 이영희 씨의 신호위반을 규명하기 위해 도로 감시 CCTV 녹화 영상 공개 및 이메일 송부를 청구함.
2. **분류(01_classification.md)**: Classifier가 민원 취지를 분석해 `일반행정/기타` 카테고리로 매핑.
3. **검색(02_laws_search.md)**: Searcher가 `laws_db.py` 및 웹 검색을 통해 정보공개법 제9조 제1항 제6호(개인정보 노출 방지를 위한 비식별 조치 의무) 및 대법원 판례(제3자 영역 모자이크 처리 후 부분공개) 조항을 인출.
4. **작성(03_draft_reply.md)**: Drafter가 1차 답변 초안을 썼으나, 본문 내에 상대 운전자 이영희 씨의 실명과 전화번호를 노출하고 영상을 메일로 그냥 보내주겠다고 기재함.
5. **검수 및 반려(04_review_report.md)**: **Reviewer Consortium**이 병렬 검수 중 개인정보 노출 및 송부 규정 위반을 적발하여 `REJECTED` 판정을 내리고 보완 피드백을 전달.
6. **최종 출력(05_final_notice.md)**: Drafter가 피드백을 수용하여 상대 운전자 이름을 `이OO 씨`로 비식별 마스킹하고, 방문 수령 절차 및 모자이크 가공 수수료 부담 규정을 정확하게 고지한 답변서를 작성하여 최종 `APPROVED` 승인을 득함.
