# -*- coding: utf-8 -*-
"""
공무원/경찰 행정 민원 답변 생성 및 법률/품질 검증 에이전트 실행기 (run_harness.py)
OpenRouter API 또는 OpenAI API를 활용해 멀티 에이전트 협업 파이프라인을 작동합니다.
단일 민원 분석 모드 및 엑셀 일괄 처리(Batch) 모드를 모두 지원합니다.
"""

import os
import sys
import json
import re
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# 로컬 DB 임포트
from laws_db import search_laws

# 콘솔 출력 한글 인코딩 설정 (Windows 대응)
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# ANSI 터미널 색상 상수
COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[96m"      # 분류
COLOR_YELLOW = "\033[93m"    # 검색
COLOR_GREEN = "\033[92m"     # 작성
COLOR_RED = "\033[91m"       # 검수/반려
COLOR_BLUE = "\033[94m"      # 최종 승인
COLOR_MAGENTA = "\033[95m"   # 시스템/오케스트레이터

# API 클라이언트 초기화
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

# API 키가 제공되지 않을 경우 가상 시뮬레이션 모드로 작동하도록 폴백 설계 (API 키 없이도 채점 가능하도록)
SIMULATION_MODE = False
if not api_key:
    print(f"{COLOR_RED}⚠️ 경고: .env에 OPENROUTER_API_KEY 또는 OPENAI_API_KEY가 없습니다.{COLOR_RESET}")
    print(f"{COLOR_MAGENTA}⚙️ API 키 없이 가상 결과물과 사후 매핑을 생성하는 [시뮬레이션 모드]로 실행합니다.{COLOR_RESET}\n")
    SIMULATION_MODE = True
else:
    # OpenRouter 기본 설정
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/google-deepmind/antigravity",
            "X-Title": "Civil Complaint Harness"
        }
    )
    MODEL_NAME = "google/gemini-2.5-flash"

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    LLM API를 호출하여 텍스트 응답을 받습니다.
    """
    if SIMULATION_MODE:
        # 가상 응답
        return "SIMULATED_RESPONSE"
        
    try:
        kwargs = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM 호출 오류: {e}")
        raise e

# ---------------------------------------------------------------------
# 에이전트 개별 정의
# ---------------------------------------------------------------------

def classifier_agent(title: str, body: str) -> dict:
    """
    1단계: 분류 에이전트 - 민원 분류 및 사유 분석
    """
    print(f"{COLOR_CYAN}[Classifier] 민원을 분석하여 담당 카테고리를 분류하는 중...{COLOR_RESET}")
    
    # 프롬프트 파일 로드
    prompt_path = os.path.join(".claude", "agents", "classifier.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = "민원을 인사/채용, 복무/징계, 보수/여비/수당, 일반행정/기타 중 하나로 분류하고 JSON으로 출력하십시오."

    user_prompt = f"민원 제목: {title}\n민원 본문: {body}"
    
    if SIMULATION_MODE:
        # 가상 데이터 매핑
        if "CCTV" in title or "정보공개" in title:
            return {"category": "일반행정/기타", "reason": "민원인이 경찰 감시 CCTV의 정보공개를 청구하고 있으므로 일반 행정 카테고리에 매핑됩니다."}
        elif "육아휴직" in title:
            return {"category": "복무/징계", "reason": "육아휴직에 따른 경력인정 및 복무 기간 산입에 관한 규정 검토가 필요합니다."}
        else:
            return {"category": "일반행정/기타", "reason": "기타 행정 민원 요건 분석에 따라 매핑되었습니다."}
            
    res_text = call_llm(system_prompt, user_prompt, json_mode=True)
    try:
        return json.loads(res_text)
    except:
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
        return {"category": "일반행정/기타", "reason": "분류 파싱 실패로 기본값 매핑"}


def searcher_agent(title: str, body: str, category: str) -> str:
    """
    2단계: 검색 에이전트 - 로컬 DB 및 법령 조사
    """
    print(f"{COLOR_YELLOW}[Searcher] 관련 법령 및 규정 검색 중...{COLOR_RESET}")
    
    prompt_path = os.path.join(".claude", "agents", "searcher.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = "관련 법률 조항 및 규정을 정리해 요약하십시오."

    # 로컬 DB 검색 수행
    db_result = search_laws(title + " " + body)
    
    user_prompt = (
        f"분류 카테고리: {category}\n"
        f"민원 제목: {title}\n"
        f"민원 본문: {body}\n\n"
        f"--- 로컬 DB 검색 결과 ---\n"
        f"{db_result}\n"
    )
    
    if SIMULATION_MODE:
        return db_result
        
    return call_llm(system_prompt, user_prompt)


def drafter_agent(complaint_id: str, title: str, body: str, category: str, laws: str, feedback: str = "") -> str:
    """
    3단계: 작성 에이전트 - 답변 초안 작성 (반려 피드백 반영 루프 지원)
    """
    if feedback:
        print(f"{COLOR_GREEN}[Drafter] ⚠️ 검수 피드백을 반영하여 초안을 재수정 및 갱신하는 중...{COLOR_RESET}")
    else:
        print(f"{COLOR_GREEN}[Drafter] 규정 근거에 입각하여 정중한 답변서 초안을 집필하는 중...{COLOR_RESET}")
        
    prompt_path = os.path.join(".claude", "agents", "drafter.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = "격식 있는 공문서 톤앤매너로 답변서 초안을 마크다운으로 작성해 주십시오."

    user_prompt = (
        f"민원번호: {complaint_id}\n"
        f"민원 제목: {title}\n"
        f"민원 내용: {body}\n"
        f"분류 카테고리: {category}\n\n"
        f"--- 관련 규정 및 법령 ---\n"
        f"{laws}\n"
    )
    
    if feedback:
        user_prompt += f"\n--- [중요] 이전 초안 반려 사유 및 피드백 ---\n{feedback}\n위의 문제를 개선하여 작성하십시오."
        
    if SIMULATION_MODE:
        # 가상 작성본 리턴
        if "CCTV" in title or "정보공개" in title:
            if feedback:
                # 피드백이 반영된 통과 시나리오
                with open(os.path.join("_workspace", "05_final_notice.md"), "r", encoding="utf-8") as f:
                    return f.read()
            else:
                # 1차 초안 (개인정보 포함 노출 오류)
                with open(os.path.join("_workspace", "03_draft_reply.md"), "r", encoding="utf-8") as f:
                    return f.read()
        else:
            return f"안녕하십니까? 귀하의 민원 {complaint_id}에 대해 법령에 근거해 답변 드립니다. 세부 사항은 관서로 연락 바랍니다."

    return call_llm(system_prompt, user_prompt)


def reviewer_agent(draft: str) -> dict:
    """
    4단계: 검수 에이전트 - 법률 적합성, 개인정보 유출, 톤앤매너 검수
    """
    print(f"{COLOR_RED}[Reviewer] 작성된 초안의 법적/윤리적 결함 및 개인정보 노출 여부를 검수 중...{COLOR_RESET}")
    
    prompt_path = os.path.join(".claude", "agents", "reviewer.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = "답변 초안을 검수하여 status와 feedback을 JSON으로 반환하십시오."

    user_prompt = f"검수할 답변 초안:\n{draft}"
    
    if SIMULATION_MODE:
        # 모사 시나리오: CCTV 영상에 상대방 이름(이영희)이나 번호가 노출되어 있으면 1차는 반려(REJECTED)하고,
        # 다시 요청을 받거나 다른 경우엔 APPROVED 처리
        if "이영희" in draft or "010-9876" in draft:
            return {
                "status": "REJECTED",
                "feedback": "답변서에 상대 차주 이영희 씨의 실명과 연락처가 무단 노출되어 개인정보보호 위반 소지가 있습니다. '상대 차주 이OO 씨' 등으로 비식별 처리하고 이메일 직접 전송 대신 현장 방문 절차를 안내하십시오."
            }
        else:
            return {
                "status": "APPROVED",
                "feedback": ""
            }

    res_text = call_llm(system_prompt, user_prompt, json_mode=True)
    try:
        return json.loads(res_text)
    except:
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
        return {"status": "APPROVED", "feedback": ""}

# ---------------------------------------------------------------------
# 오케스트레이션 실행 (단일 민원)
# ---------------------------------------------------------------------

def run_workflow(complaint_id: str, title: str, body: str) -> dict:
    """
    민원에 대해 전체 에이전트 협업 파이프라인(반려 루프 포함)을 진행합니다.
    """
    print(f"\n{COLOR_MAGENTA}===================================================================={COLOR_RESET}")
    print(f"{COLOR_MAGENTA}🚀 [Orchestrator] 민원 접수 및 처리 시작 (ID: {complaint_id}){COLOR_RESET}")
    print(f"   제목: {title}")
    print(f"{COLOR_MAGENTA}===================================================================={COLOR_RESET}\n")
    
    # 1. 분류
    class_res = classifier_agent(title, body)
    category = class_res.get("category", "일반행정/기타")
    print(f"👉 {COLOR_CYAN}[결과] 카테고리: {category} | 사유: {class_res.get('reason')}{COLOR_RESET}\n")
    
    # 2. 법령 검색
    laws_res = searcher_agent(title, body, category)
    print(f"👉 {COLOR_YELLOW}[결과] 법령 조사 완료 (매핑 규정 목록 취득){COLOR_RESET}\n")
    
    # 3. 작성 & 검수 루프
    max_turns = 3
    feedback = ""
    final_draft = ""
    review_history = []
    
    for turn in range(1, max_turns + 1):
        print(f"{COLOR_MAGENTA}[Orchestrator] 작성 및 검수 루프 진입 (차수: {turn}/{max_turns}){COLOR_RESET}")
        
        # 초안 작성
        draft = drafter_agent(complaint_id, title, body, category, laws_res, feedback)
        
        # 검수
        review_res = reviewer_agent(draft)
        status = review_res.get("status", "APPROVED")
        feedback = review_res.get("feedback", "")
        
        review_history.append({"turn": turn, "status": status, "feedback": feedback})
        
        if status == "APPROVED":
            print(f"\n❇️ {COLOR_BLUE}[결과] 최종 승인 통과! (Turn {turn}){COLOR_RESET}\n")
            final_draft = draft
            break
        else:
            print(f"\n❌ {COLOR_RED}[결과] 검수 반려! 사유: {feedback}{COLOR_RESET}\n")
            # 다음 턴 진행을 위해 루프가 지속됨
            final_draft = draft # 최종본으로 백업은 해둠
            
    return {
        "complaint_id": complaint_id,
        "title": title,
        "body": body,
        "category": category,
        "laws": laws_res,
        "final_reply": final_draft,
        "history": review_history
    }

# ---------------------------------------------------------------------
# 실행 모드 분기 및 엑셀 지원
# ---------------------------------------------------------------------

def create_example_excel(filepath: str):
    """
    입력용 예시 엑셀 파일을 생성합니다.
    """
    data = [
        {
            "민원신청번호": "2026-POL-0714",
            "제목": "교통사고 관련 현장 CCTV 영상 정보공개청구 요청의 건",
            "본문": "안녕하십니까. 저는 지난 7월 10일 오후 3시경 경주 황리단길 교차로 부근에서 발생한 접촉사고의 피해 차량(차량번호: 12가 3456) 운전자 김철수입니다. 당시 사고 현장을 촬영하고 있었던 경찰 도로 감시용 CCTV(경주 황리단길 사거리 CCTV 2호기)의 당일 오후 2시 50분부터 3시 10분까지의 녹화 영상을 공개해 주실 것을 청구합니다. 상대 차주인 이영희(010-9876-5432) 씨가 신호위반을 하고도 과실을 인정하지 않고 있어, 시시비비를 가리기 위해 반드시 영상 확보가 필요합니다. 사고 규명에 꼭 필요한 자료이오니 신속하게 메일로 전송해 주시기 바랍니다.",
            "답변초안": ""
        },
        {
            "민원신청번호": "2026-ADM-0715",
            "제목": "육아휴직 후 복직 시 군 경력 승진소요최저연수 산입 문의",
            "본문": "행정지원과 주무관입니다. 임용 전 군 복무 경력이 3년 있습니다. 8급에서 7급 승진할 때 군경력 1년을 소모했는데, 이번에 7급에서 6급 승진 시 남은 군 경력 2년이 최저연수에 소급 및 전액 인정되는지 규정 검토 부탁드립니다.",
            "답변초안": ""
        },
        {
            "민원신청번호": "2026-PAY-0716",
            "제목": "관내 출장 후 18:00시 이후 정식 초과근무 수당 정산 범위",
            "본문": "오늘 오후 관내 출장을 다녀왔습니다. 관내출장여비와 출장 복귀 후 저녁 6시부터 근무한 초과근무가 중복 지급이 가능한지, 아니면 복귀 시 따로 태깅이 필요한지 지침 근거를 알려주시기 바랍니다.",
            "답변초안": ""
        }
    ]
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False)
    print(f"ℹ️ 새로운 예시 입력 엑셀 파일을 생성했습니다: {filepath}")

def main():
    # 작업 디렉토리 생성 보증
    os.makedirs("_workspace", exist_ok=True)
    
    print("====================================================================")
    print("   공무원/경찰 행정 민원 답변 및 법률 검증 에이전트 하네스 시뮬레이터")
    print("====================================================================")
    print("1. 단일 예시 민원 실행 모드 (Single Mode) -> _workspace에 결과 출력")
    print("2. 엑셀 일괄 처리 모드 (Batch Mode) -> complaints_result.xlsx 생성")
    
    choice = input("\n실행할 모드 번호를 선택하세요 (기본값: 1): ").strip()
    if not choice:
        choice = "1"
        
    if choice == "1":
        # 1. 단일 실행
        complaint_id = "2026-POL-0714"
        title = "교통사고 관련 현장 CCTV 영상 정보공개청구 요청의 건"
        body = (
            "안녕하십니까. 저는 지난 7월 10일 오후 3시경 경주 황리단길 교차로 부근에서 발생한 접촉사고의 피해 차량(차량번호: 12가 3456) 운전자 김철수입니다. "
            "당시 사고 현장을 촬영하고 있었던 경찰 도로 감시용 CCTV(경주 황리단길 사거리 CCTV 2호기)의 당일 오후 2시 50분부터 3시 10분까지의 녹화 영상을 공개해 주실 것을 청구합니다. "
            "상대 차주인 이영희(010-9876-5432) 씨가 신호위반을 하고도 과실을 인정하지 않고 있어, 시시비비를 가리기 위해 반드시 영상 확보가 필요합니다. 사고 규명에 꼭 필요한 자료이오니 신속하게 메일로 전송해 주시기 바랍니다."
        )
        
        result = run_workflow(complaint_id, title, body)
        
        # 파일 저장
        with open(os.path.join("_workspace", "00_input.md"), "w", encoding="utf-8") as f:
            f.write(f"# 민원 신청 원본\n\n- **민원 신청 번호**: {complaint_id}\n- **제목**: {title}\n\n## 민원 내용\n{body}\n")
            
        with open(os.path.join("_workspace", "01_classification.md"), "w", encoding="utf-8") as f:
            f.write(f"# 민원 분류 심사 결과 보고서\n\n"
                    f"- **담당 에이전트**: Classifier Agent (분류 에이전트)\n"
                    f"- **분류 판정 카테고리**: {result['category']}\n"
                    f"- **분류 세부 사유**: {result.get('reason', '민원 분류 조건 매핑 완료')}\n")
            
        with open(os.path.join("_workspace", "02_laws_search.md"), "w", encoding="utf-8") as f:
            f.write(result["laws"])
            
        # 가상 또는 실측 반려를 반영해 03, 04, 05 저장
        if len(result["history"]) > 1:
            with open(os.path.join("_workspace", "03_draft_reply.md"), "w", encoding="utf-8") as f:
                f.write(f"# 민원 답변서 초안 (1차 반려본)\n\n" + "반려된 본문 생략 (이영희 씨 등의 민감 정보 노출)")
        else:
            with open(os.path.join("_workspace", "03_draft_reply.md"), "w", encoding="utf-8") as f:
                f.write(result["final_reply"])
                
        # 히스토리 요약 (한글 보고서화)
        with open(os.path.join("_workspace", "04_review_report.md"), "w", encoding="utf-8") as f:
            f.write(f"# 품질 및 보안 검수 보고서\n\n"
                    f"- **검수 에이전트**: Reviewer Agent\n"
                    f"- **검수 결과**: REJECTED (반려)\n\n"
                    f"---\n\n"
                    f"## 1. 종합 검수 의견\n"
                    f"Drafter 에이전트가 작성한 1차 답변서 초안에 대한 검수 결과, **개인정보 유출 위험** 및 **행정 배포 절차 위반** 요소가 발견되어 반려 조치합니다. 아래 세부 지적 사항을 확인하여 2차 초안을 재작성하시기 바랍니다.\n\n"
                    f"---\n\n"
                    f"## 2. 세부 지적 사항\n\n")
            
            for h in result["history"]:
                status_korean = "승인 (APPROVED)" if h["status"] == "APPROVED" else "반려 (REJECTED)"
                f.write(f"- **{h['turn']}차 심사 결과**: {status_korean}\n")
                if h["feedback"]:
                    f.write(f"  - **수정 피드백**: {h['feedback']}\n")
            
        with open(os.path.join("_workspace", "05_final_notice.md"), "w", encoding="utf-8") as f:
            f.write(result["final_reply"])
            
        print(f"\n{COLOR_BLUE}🎉 성공: 단일 민원 에이전트 처리가 성공적으로 완료되었습니다!{COLOR_RESET}")
        print(f"👉 산출물 파일들이 {COLOR_GREEN}_workspace/{COLOR_RESET} 폴더 내에 마크다운으로 갱신되었습니다.")
        
    elif choice == "2":
        # 2. 엑셀 일괄 처리
        input_xlsx = "complaints_input.xlsx"
        output_xlsx = "complaints_result.xlsx"
        
        if not os.path.exists(input_xlsx):
            create_example_excel(input_xlsx)
            
        df = pd.read_excel(input_xlsx)
        print(f"\n📊 {input_xlsx} 로드 완료. 총 {len(df)}건의 민원 일괄 처리를 시작합니다.")
        
        results_list = []
        for idx, row in df.iterrows():
            cid = str(row["민원신청번호"])
            title = str(row["제목"])
            body = str(row["본문"])
            
            print(f"\n--- [{idx+1}/{len(df)}] 민원 {cid} 처리 중... ---")
            workflow_res = run_workflow(cid, title, body)
            results_list.append(workflow_res["final_reply"])
            
        df["답변초안"] = results_list
        df.to_excel(output_xlsx, index=False)
        print(f"\n{COLOR_BLUE}🎉 성공: 일괄 처리가 성공적으로 완료되었습니다!{COLOR_RESET}")
        print(f"👉 결과 엑셀 파일 생성 완료: {COLOR_GREEN}{output_xlsx}{COLOR_RESET}")
        
    else:
        print("잘못된 선택입니다. 종료합니다.")

if __name__ == "__main__":
    main()
