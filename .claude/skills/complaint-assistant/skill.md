# Complaint Assistant Orchestrator Skill

행정 민원 처리의 다단계 병렬 검수 및 합의(Consensus) 오케스트레이션을 정의하는 제어 흐름 규격입니다.

## 에이전트 아키텍처 및 데이터 흐름

본 시스템은 단일 에이전트의 판단 오류(Hallucination)를 예방하기 위해, 답변 초안을 3인의 전문 검수 에이전트가 **병렬로 동시 심사(Parallel Evaluation)**하고 최종 오케스트레이터가 합의안을 도출하는 아키텍처로 구성됩니다.

```mermaid
graph TD
    Input[민원 신청서] --> Classifier[Classifier Agent]
    Classifier -->|카테고리 분류 결과| Searcher[Searcher Agent: 로컬 DB + 실시간 웹 검색]
    Searcher -->|법률 근거 취합| Drafter[Drafter Agent: 공문서 답변 집필]
    Drafter -->|답변서 초안 송신| ParallelReview{병렬 검수 에이전트 팀}
    
    subgraph Reviewer Consortium (병렬 검수단)
        ParallelReview --> Reviewer1[Legal Auditor: 법률 정합성]
        ParallelReview --> Reviewer2[Privacy Inspector: 개인정보 필터링]
        ParallelReview --> Reviewer3[PR Officer: 대민 톤앤매너]
    end
    
    Reviewer1 --> Consensus{최종 합의 및 조율}
    Reviewer2 --> Consensus
    Reviewer3 --> Consensus
    
    Consensus -->|반려 REJECTED: 수정 피드백| Drafter
    Consensus -->|승인 APPROVED| Output[최종 정보공개 결정통지서 출력]
```

## 에이전트 역할 매핑

- **Classifier (분류)**: `agents/classifier.md` 정의 준수.
- **Searcher (법령/웹 검색)**: `agents/searcher.md` 정의 준수.
- **Drafter (답변 집필)**: `agents/drafter.md` 정의 준수.
- **Reviewer Consortium (병렬 검수단)**:
  - **Legal Auditor (법률 검수관)**: 검색된 근거 법령이 누락되거나 왜곡 인용되지 않았는지 법률 적합성 평정.
  - **Privacy Inspector (개인정보 검수관)**: 제3자 실명, 연락처 등 고유식별정보의 노출 여부 평정.
  - **PR Officer (대민 검수관)**: 민원인에 대한 어투의 적절성 및 두괄식 가독성 평정.

## 실행 흐름 규정 (Consensus Algorithm)

1. **입력 및 정제**: 민원인의 ID, 제목, 본문 데이터를 수집합니다.
2. **분류 (Classifier)**: 인사/채용, 복무/징계, 보수/여비/수당, 일반행정/기타 카테고리 확정 및 사유 기록.
3. **추출 및 실시간 웹 검색 (Searcher)**:
   - 1차: 로컬 DB 내 키워드 검색 수행.
   - 2차: `WebSearchTool`을 사용하여 인사혁신처 및 정부 공식 채널의 최신 유권해석 및 개정 법령 동적 갱신.
4. **초안 작성 (Drafter)**: 수집된 정보를 취합하여 5단계 대한민국 표준 공문 서식에 맞춰 답변서 초안 작성.
5. **병렬 검수 심사 (Parallel Reviewing)**:
   - Drafter가 작성한 초안을 **Legal Auditor**, **Privacy Inspector**, **PR Officer**에게 동시에 송신합니다.
   - 각 에이전트는 독립적으로 JSON 형태로 심사 결과를 출력합니다.
6. **합의(Consensus) 판단**:
   - 오케스트레이터는 3인의 심사 결과 중 단 하나라도 `REJECTED`가 있을 경우, 각 에이전트의 수정 피드백을 수집·통합하여 Drafter에게 **일괄 반려**합니다.
   - 3인 전원 `APPROVED`일 경우에만 최종 결재가 완료되어 발송 대기 상태로 이행합니다.
7. **피드백 재작성 루프**:
   - 반려 시, Drafter는 통합 피드백을 분석하여 결함을 보완하고 재작성합니다. (최대 3회 제한)
8. **최종 시행**: 승인된 문서를 마크다운 및 공문서 포맷으로 출력하여 _workspace에 영구 저장합니다.
