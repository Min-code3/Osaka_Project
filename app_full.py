import streamlit as st
import pandas as pd
import base64
import os
import folium
from streamlit_folium import st_folium
import logging
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import csv
from openai import OpenAI
import streamlit.components.v1 as components 

# ==========================================
# [0] 페이지 기본 설정 (가장 먼저 실행)
# ==========================================
st.set_page_config(page_title="AI & Travel Curator", page_icon="🇯🇵", layout="wide")

# ==========================================
# [0-1] 구글 시트 & 로그 설정 (전역 함수)
# ==========================================
# 이 함수들을 맨 위로 올려서 AI봇과 장소추천 양쪽에서 다 쓰게 만듭니다.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@st.cache_resource
def get_google_sheet_connection():
    try:
        # st.secrets에 gcp_service_account 정보가 있어야 함
        if "gcp_service_account" not in st.secrets: return None
        secrets = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e: 
        print(f"Sheet Connection Error: {e}")
        return None

def save_log_to_sheet(log_data):
    """
    구글 시트에 데이터를 한 줄 추가하는 함수
    log_data 리스트 형식: [시간, 사용자ID, 행동(Action), 상세내용(Details)]
    """
    try:
        client = get_google_sheet_connection()
        if client:
            # 🔴 사용하시는 시트 ID와 시트 이름이 맞는지 확인하세요
            sheet_id = "1aEKUB0EBFApDKLVRd7cMbJ6vWlR7-yf62L5MHqMGvp4" 
            spreadsheet = client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet("Logs_ai") # 워크시트 이름 확인
            worksheet.append_row(log_data)
    except Exception as e: 
        print(f"Save Log Error: {e}")

def get_current_time():
    try:
        kst = pytz.timezone('Asia/Seoul') 
        return datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# [0-2] 모드 선택 (메인 화면 상단 배치)
# ==========================================
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "ai_bot"
if "visitor_id" not in st.session_state:
    st.session_state.visitor_id = st.query_params.get("id", "anonymous")

# 사이드바 제거하고 바로 메인 화면에 버튼 배치
col_nav1, col_nav2 = st.columns(2)

with col_nav1:
    if st.button("🤖 AI 여행 비서 (챗봇)", use_container_width=True):
        st.session_state.app_mode = "ai_bot"
        st.rerun()

with col_nav2:
    if st.button("📍 맞춤 장소 추천 (큐레이션)", use_container_width=True):
        st.session_state.app_mode = "place_rec"
        st.rerun()

st.divider() 

# ==========================================
# [기능 1] AI 여행 비서 (챗봇)
# ==========================================
if st.session_state.app_mode == "ai_bot":
    
    # 1. API 키 설정
    if "openai_api_key" in st.secrets:
        api_key = st.secrets["openai_api_key"]
    else:
        st.error("OpenAI API 키가 설정되지 않았습니다.")
        st.stop()

    client = OpenAI(api_key=api_key)

    # 2. 화면 구성
    st.title("🇯🇵 일본 여행 비서")

    selected_region = st.radio(
        "여행 중인 지역을 선택해주세요",
        ["전체", "오사카", "교토"],
        horizontal=True
    )
    st.caption(f"현재 설정된 지역: **{selected_region}**")

    # 3. 프롬프트
    base_system_instruction = """
    너는 일본 여행을 도와주는 친절하고 유능한 AI 비서다.

    한국어로 자연스럽게 대화해라.



    [🚨 절대 금지 사항 (위반 시 시스템 오류 간주)]

    1. **카테고리/지역명 링크 금지**: '오사카 맛집', '나카노시마 카페', '추천 식당' 같은 **일반 명사나 제목**에는 절대로 구글맵 링크를 걸지 마라. 오직 **특정 가게 이름**에만 링크를 걸어야 한다.

    - 나쁜 예: 이번에는 [나카노시마 카페](...)를 소개할게. (절대 금지)

    - 좋은 예: 이번에는 나카노시마 주변의 카페를 소개할게.

    2. **검색 쿼리 왜곡 금지**: 구글맵 링크 생성 시, 유저가 말한 지역명을 억지로 상호명 뒤에 붙이지 마라.

    - 나쁜 예: query=브루클린 로스팅 컴퍼니 나카노시마 (지점명이 틀릴 수 있음)

    - 좋은 예: query=Brooklyn Roasting Company (상호명만 깔끔하게)

    - 좋은 예: query=Brooklyn Roasting Company Kitahama (정확한 지점명을 아는 경우)



    [요청사항]

    최우선 요청사항 : 할루시네이션은 절대 금물. 절대절대 하지마

    0. 항상 사용자가 해외에 있음을 유념해서 답변해줘

    **구글맵 링크 필수**: 장소를 언급할 때는 사용자가 바로 찾을 수 있게 아래의 '검색 링크' 형식을 무조건 따라라. 가짜 URL을 만들지 말고 검색 쿼리를 써라.

    - 형식: `[장소명 구글맵 검색](https://www.google.com/maps/search/?api=1&query=장소명+지역명)`

    - 예시: `[이치란 라멘 구글맵 검색](https://www.google.com/maps/search/?api=1&query=이치란라멘+오사카)`

    2. **제품 추천**: 아플 때나 필요한 물건이 있을 때는 제품명(한국어/일본어), 추천 이유, 파는 곳(돈키호테, 드럭스토어 등)을 명시해라.

    3. **위치 확인**: 식당 추천 요청 시 유저의 위치를 모르면 먼저 물어봐라.

    4. **말투**: 공감이나 서론/결론의 군더더기를 빼고, 친구처럼 담백하게 핵심 정보만 전달해라.

    5. **해외 상황 고려**: 사용자가 현재 데이터 로밍 중일 수 있으니 텍스트를 너무 길게 쓰지 말고 가독성 있게 끊어 써라.

    6. 존댓말 써
    """

    # 4. 로그 저장 (CSV + 구글 시트 둘 다 저장)
    def save_chat_log(role, content):
        timestamp = get_current_time()
        
        # (1) 로컬 CSV 저장 (백업용)
        file_name = 'chat_log.csv'
        file_exists = os.path.isfile(file_name)
        with open(file_name, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["시간", "주체", "내용"])
            writer.writerow([timestamp, role, content])
            
        # (2) 🔥 구글 시트 저장 (추가된 부분)
        # 형식: [시간, 사용자ID, 역할(Action), 내용(Details)]
        save_log_to_sheet([timestamp, st.session_state.visitor_id, f"AI_CHAT_{role}", content])

    # 5. 채팅 UI
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문 입력"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_chat_log("User", prompt) # 로그 저장 함수 변경됨

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            final_system_instruction = base_system_instruction
            if selected_region == "오사카":
                final_system_instruction += "\n\n[강제 지침] 질문에 지역명이 없어도 무조건 '오사카' 정보를 답변해라."
            elif selected_region == "교토":
                final_system_instruction += "\n\n[강제 지침] 질문에 지역명이 없어도 무조건 '교토' 정보를 답변해라."
            
            history = [{"role": "system", "content": final_system_instruction}] + st.session_state.messages

            try:
                stream = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=history,
                    stream=True,
                    temperature=0, 
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                save_chat_log("AI", full_response) # 로그 저장 함수 변경됨

            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")


# ==========================================
# [기능 2] 장소 추천 서비스 (큐레이션)
# ==========================================
elif st.session_state.app_mode == "place_rec":

    # [1] 데이터 로드 및 유틸리티
    # (구글 시트 연결 함수는 맨 위 [0-1]로 이동했으므로 여기서 제거)

    # 장소 추천용 로그 래퍼 함수
    def log_action(action, details=""):
        now = get_current_time()
        visitor_id = st.session_state.visitor_id
        
        # 화면 출력용 로그
        log_msg = f"[{now}] ACTION: {action} | DETAILS: {details}"
        logger.info(log_msg) 
        
        # 구글 시트 저장 (전역 함수 호출)
        save_log_to_sheet([now, visitor_id, action, details])

    def clean_filename(name):
        return "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in name]).strip()

    @st.cache_data 
    def get_local_image_html(file_path, height="200px", radius="8px"):
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            img_style = f'width: 100%; height: {height}; object-fit: cover; border-radius: {radius}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'
            return f'<img src="data:image/jpeg;base64,{encoded}" style="{img_style}">'
        else:
            return f'<div style="width:100%; height:{height}; background-color:#f8f9fa; border-radius:{radius}; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#adb5bd; font-size:12px;"><span>No Image</span></div>'

    @st.cache_data(ttl=600)
    def load_data():
        sheet_id = "1aEKUB0EBFApDKLVRd7cMbJ6vWlR7-yf62L5MHqMGvp4"
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0"
        try:
            df = pd.read_csv(sheet_url)
            df = df.fillna("")
            
            if 'Type' in df.columns:
                df['Type'] = df['Type'].astype(str)
                df['Type'] = df['Type'].str.replace(r'\.0$', '', regex=True)
                df['Type'] = df['Type'].replace('nan', '')

            if 'Deep_Time' in df.columns:
                df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
                df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
            
            if '위도' in df.columns: 
                df = df.rename(columns={'위도': 'lat', '경도': 'lon'})
                df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
                df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            return df
        except: return pd.DataFrame()

    df = load_data()

    # [3] 세션 상태 & 화면 이동
    if 'page' not in st.session_state: st.session_state.page = 'survey'
    if 'previous_page' not in st.session_state: st.session_state.previous_page = 'survey'

    if 'current_place' not in st.session_state: st.session_state.current_place = None
    if 'user_type' not in st.session_state: st.session_state.user_type = 0
    if 'current_region' not in st.session_state: st.session_state.current_region = "오사카"

    if 'survey_step' not in st.session_state: st.session_state.survey_step = 1
    if 'survey_answers' not in st.session_state: st.session_state.survey_answers = {'q1': None, 'q2': None}
    if 'swap_q1' not in st.session_state: st.session_state.swap_q1 = random.choice([True, False])
    if 'swap_q2' not in st.session_state: st.session_state.swap_q2 = random.choice([True, False])

    def go_page_recommendation(selected_type_val):
        st.session_state.previous_page = st.session_state.page 
        st.session_state.user_type = selected_type_val
        st.session_state.page = 'recommendation'
        log_action("GO_REC", f"Type: {selected_type_val}")
        st.rerun()

    def go_page_all_places():
        st.session_state.previous_page = st.session_state.page 
        st.session_state.page = 'all_places'
        log_action("GO_ALL", "Viewed all places")
        st.rerun()

    def go_detail(row):
        st.session_state.previous_page = st.session_state.page
        st.session_state.current_place = row
        st.session_state.page = 'detail'
        log_action("VIEW_DETAIL", f"Place: {row['Name_KR']}")

    def go_back():
        st.session_state.page = st.session_state.previous_page
        st.session_state.current_place = None
        log_action("NAV_BACK", "Back button clicked")
        st.rerun()

    def go_retake_survey():
        st.session_state.page = 'survey'
        st.session_state.user_type = 0
        st.session_state.survey_step = 1 
        st.session_state.survey_answers = {'q1': None, 'q2': None}
        st.session_state.swap_q1 = random.choice([True, False])
        st.session_state.swap_q2 = random.choice([True, False])
        log_action("RETAKE_SURVEY", "Restarted survey")
        st.rerun()

    # [4] 텍스트 설정 & DB 매핑
    TYPE_MAPPING = {
        "여행자 타입": "근랜드",
        "낭만가 타입": "원랜드",
        "탐험가 타입": "모험",
        "사색가 타입": "조용"
    }
    REVERSE_TYPE_MAPPING = {v: k for k, v in TYPE_MAPPING.items()}

    col_h1, col_h2 = st.columns([8, 2])
    with col_h2:
        language = st.radio("Language", ["한국어", "English"], horizontal=True, label_visibility="collapsed")

    if language == "한국어":
        cols = {'name': 'Name_KR', 'desc': 'Description_KR', 'loc': 'Landmark_KR', 'cat': 'Category_KR', 'grp': 'Group_KR', 'tag': 'Tag_KR', 'area': 'Area_KR', 'map': 'Google_Map_KR'}
        txt = {
            'title': "오사카/교토 여행지 리스트", 
            'survey_title': "여행에서 더 끌리는 곳",
            'survey_sub': "", 
            'q1_landmark': "사람은 많아도, 유명한 랜드마크", 
            'q1_local': "숨겨진 한적한 로컬 스팟",
            'q2b_title': "더 선호하는 랜드마크",
            'q2b_crowded': "사람은 많아도, 가까운 곳", 
            'q2b_far': "조금 멀어도, 덜 붐비는 곳",        
            'q2a_title': "로컬 스팟을 원하는 이유",
            'q2a_adventure': "남들이 가지 않는 장소를 가보고 싶어서", 
            'q2a_quiet': "너무 많은 인파는 부담스러워서",        
            'btn_select': "선택",
            'region_label': "도시",
            'regions': ["오사카", "교토"],
            'type_label': "어디로 갈까요?",
            'quick_type_label': "",
            'cats': ["자연", "도시", "역사/전통", "휴식", "쇼핑"],
            'grps': ["혼자", "연인", "친구", "부모님", "어린이"],
            'btns': ["여행자 타입", "낭만가 타입", "탐험가 타입", "사색가 타입"],
            'res': "검색 결과",
            'no_res': "조건을 만족하는 장소를 찾기 어렵습니다.",
            'dtl_btn': "상세보기",
            'back': "뒤로가기",
            'rec_title': "성향에 맞는 장소 추천",
            'rec_reset': "다시 테스트",
            'go_all': "전체 장소 보기",
            'type_messages': {
                "근랜드": "여행자 타입 : 상징적인 랜드마크",
                "원랜드": "낭만가 타입 : 여유롭게 즐기는 랜드마크",
                "모험": "탐험가 타입 : 낯선 곳에서 마주하는 로컬 분위기",
                "조용": "사색가 타입 : 복잡한 인파에서 벗어난 차분한 분위기"
            }
        }
    else:
        cols = {'name': 'Name_EN', 'desc': 'Description_EN', 'loc': 'Landmark_EN', 'cat': 'Category_EN', 'grp': 'Group_EN', 'tag': 'Tag_EN', 'area': 'Area_EN', 'map': 'Google_Map_EN'}
        txt = {
            'title': "Osaka/Kyoto Travel List",
            'survey_title': "Preferred Travel Destinations", 
            'survey_sub': "",
            'q1_landmark': "A Famous Landmark, Even If It’s Crowded",
            'q1_local': "A Hidden Local Spot, Even If It’s Less Known", 
            'q2b_title': "Preferred Landmark Type",
            'q2b_crowded': "Accessible City Center",
            'q2b_far': "Relaxed Outskirts",
            'q2a_title': "Reason for Local Preference",
            'q2a_adventure': "To Explore Undiscovered Places", 
            'q2a_quiet': "To Avoid Crowds",
            'btn_select': "Select",
            'region_label': "City",
            'regions': ["Osaka", "Kyoto"],
            'type_label': "Where to go?",
            'quick_type_label': "",
            'cats': ["Nature", "City", "History", "Relax", "Shopping"],
            'grps': ["Solo", "Couple", "Friends", "Parents", "Kids"],
            'btns': ["The Traveler Type", "The Romantic Type", "The Explorer Type", "The Contemplative Type"], 
            'res': "Results",
            'no_res': "No places found matching your criteria.",
            'dtl_btn': "View Details",
            'back': "Back",
            'rec_title': "Recommended Places",
            'rec_reset': "Retest",
            'go_all': "View All Places",
            'type_messages': {
                "근랜드": "The Traveler Type: Nearby Iconic Landmarks",
                "원랜드": "The Romantic Type: Savoring Landmarks at a Leisurely Pace",
                "모험": "The Explorer Type: Immersing in Local Atmospheres off the Map",
                "조용": "The Contemplative Type: Calm Spaces Away from the Crowds"
            }
        }

    if language != "한국어":
        TYPE_MAPPING = {
            "The Traveler Type": "근랜드",
            "The Romantic Type": "원랜드",
            "The Explorer Type": "모험",
            "The Contemplative Type": "조용"
        }
        REVERSE_TYPE_MAPPING = {v: k for k, v in TYPE_MAPPING.items()}


    if st.session_state.page != 'detail':
        st.title(txt['title'])

    # [오류 방지]
    if st.session_state.current_region not in txt['regions']:
        st.session_state.current_region = txt['regions'][0]

    # [PAGE 1] 설문조사
    if st.session_state.page == 'survey':
        st.write(f"**{txt['region_label']}**")
        new_region = st.radio(
            "Region_Survey", 
            txt['regions'], 
            index=txt['regions'].index(st.session_state.current_region), 
            horizontal=True, 
            label_visibility="collapsed"
        )
        if new_region != st.session_state.current_region:
            log_action("REGION_CHANGE", f"Changed to {new_region}")
            st.session_state.current_region = new_region
            st.rerun()

        st.divider()

        if st.session_state.survey_step == 1:
            if st.button(txt['go_all'], type="secondary", use_container_width=True):
                go_page_all_places()
            st.markdown("---")

        if "Kyoto" in st.session_state.current_region or "교토" in st.session_state.current_region:
            region_tag = "kyoto"
        else:
            region_tag = "osaka"

        def get_img_path(base_name):
            return os.path.join("images", f"{base_name}_{region_tag}.jpg")

        current_title = txt['survey_title']
        if st.session_state.survey_step == 2:
            if st.session_state.survey_answers['q1'] == 'landmark':
                current_title = txt['q2b_title']
            elif st.session_state.survey_answers['q1'] == 'local':
                current_title = txt['q2a_title']

        st.subheader(current_title)
        IMG_HEIGHT = "250px"

        def render_option(img_key, txt_key, val):
            st.markdown(get_local_image_html(get_img_path(img_key), height=IMG_HEIGHT), unsafe_allow_html=True)
            
            if st.button(txt[txt_key], key=f"btn_{img_key}", use_container_width=True):
                log_action("SURVEY_CHOICE", f"Step:{st.session_state.survey_step} | Selected:{val}")

                if st.session_state.survey_step == 1:
                    st.session_state.survey_answers['q1'] = val
                    st.session_state.survey_step = 2
                    st.rerun()
                else:
                    go_page_recommendation(val)

        if st.session_state.survey_step == 1:
            col1, col2 = st.columns(2)
            opt_a = ("q1_landmark", "q1_landmark", "landmark")
            opt_b = ("q1_local", "q1_local", "local")
            
            if st.session_state.swap_q1: left, right = opt_b, opt_a
            else: left, right = opt_a, opt_b
                
            with col1: render_option(*left)
            with col2: render_option(*right)

        elif st.session_state.survey_step == 2:
            if st.button(f"⬅️ {txt['back']}"): 
                log_action("SURVEY_BACK", "Returned to Step 1")
                st.session_state.survey_step = 1
                st.rerun()
                
            col3, col4 = st.columns(2)
            
            if st.session_state.survey_answers['q1'] == 'landmark':
                opt_a = ("q2b_crowded", "q2b_crowded", "근랜드") 
                opt_b = ("q2b_far", "q2b_far", "원랜드")           
            elif st.session_state.survey_answers['q1'] == 'local':
                opt_a = ("q2a_adventure", "q2a_adventure", "모험") 
                opt_b = ("q2a_quite", "q2a_quiet", "조용")           
                
            if st.session_state.swap_q2: left, right = opt_b, opt_a
            else: left, right = opt_a, opt_b
            
            with col3: render_option(*left)
            with col4: render_option(*right)

        st.divider()

    # [PAGE 2] 추천 결과
    elif st.session_state.page == 'recommendation':
        
        c_back, c_all = st.columns(2)
        with c_back:
            if st.button(txt['back'], use_container_width=True): go_back() 
        with c_all:
            if st.button(txt['go_all'], use_container_width=True): go_page_all_places()
        
        st.divider()

        with st.container():
            st.write(f"**{txt['region_label']}**")
            new_region = st.radio(
                "Region_Rec", 
                txt['regions'], 
                index=txt['regions'].index(st.session_state.current_region), 
                horizontal=True, 
                label_visibility="collapsed"
            )
            if new_region != st.session_state.current_region:
                st.session_state.current_region = new_region
                log_action("REGION_CHANGE", f"Changed to {new_region}")
                st.rerun()

        filtered_df = df.copy()

        if st.session_state.current_region == txt['regions'][1]: 
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('교토|기온', na=False)]
        else: 
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('난바|우메다', na=False)]

        user_result_db = st.session_state.user_type 
        custom_message = txt['type_messages'].get(user_result_db, "")
        st.success(f"**{custom_message}**")

        if 'Type' in filtered_df.columns and user_result_db:
            target = str(user_result_db)
            def is_main_tag(val):
                tags = [t.strip() for t in str(val).split(',')]
                if not tags: return False
                return tags[0] == target
            def is_any_tag(val):
                tags = [t.strip() for t in str(val).split(',')]
                return target in tags

            main_matches = filtered_df[filtered_df['Type'].apply(is_main_tag)]
            if len(main_matches) >= 3: filtered_df = main_matches
            else: filtered_df = filtered_df[filtered_df['Type'].apply(is_any_tag)]

        st.subheader(f"{txt['res']}: {len(filtered_df)}")
        st.write("")

        if len(filtered_df) == 0: st.warning(txt['no_res'])
        else:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    c_img, c_txt = st.columns([1, 2])
                    with c_img:
                        name_en = clean_filename(str(row['Name_EN']))
                        img_path = os.path.join("images", f"{name_en}.jpg")
                        st.markdown(get_local_image_html(img_path, height="120px", radius="8px"), unsafe_allow_html=True)
                    with c_txt:
                        st.markdown(f"**{row[cols['name']]}**")
                        desc_text = str(row[cols['desc']])
                        if len(desc_text) > 40: desc_text = desc_text[:40] + "..."
                        st.write(f"<span style='font-size:14px; color:#666;'>{desc_text}</span>", unsafe_allow_html=True)
                        st.caption(f"📍 {row[cols['area']]} | ⏱️ {row['Deep_Time']} min")
                        if st.button(txt['dtl_btn'], key=f"btn_rec_{idx}", use_container_width=True):
                            go_detail(row)
                            st.rerun()

        st.divider()
        if st.button(txt['rec_reset']): 
            go_retake_survey()

    # [PAGE 3] 전체 장소 리스트
    elif st.session_state.page == 'all_places':
        
        if st.button(txt['back'], use_container_width=True):
            go_back()
        
        st.divider()

        with st.container():
            st.write(f"**{txt['region_label']}**")
            new_region = st.radio(
                "Region_All", 
                txt['regions'], 
                index=txt['regions'].index(st.session_state.current_region), 
                horizontal=True, 
                label_visibility="collapsed"
            )
            if new_region != st.session_state.current_region:
                st.session_state.current_region = new_region
                log_action("REGION_CHANGE", f"Changed to {new_region}")
                st.rerun()

        filtered_df = df.copy()

        if st.session_state.current_region == txt['regions'][1]:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('교토|기온', na=False)]
        else:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('난바|우메다', na=False)]

        st.markdown("---")
        
        st.write(f"**{txt['type_label']} (Filter)**")
        selected_display_types = st.pills("Type", txt['btns'], selection_mode="multi", label_visibility="collapsed")
        
        st.write("")
        st.write("🔎 **Category & Group Filter**")
        c1, c2 = st.columns(2)
        with c1:
            st.write("🏷️ **Category**")
            sel_cats = st.pills("Cats", txt['cats'], selection_mode="multi", label_visibility="collapsed")
        with c2:
            st.write("👥 **Group**")
            sel_grps = st.pills("Grps", txt['grps'], selection_mode="multi", label_visibility="collapsed")

        # [로그] 필터 변경 상세 기록
        current_filter_state = f"Region:{st.session_state.current_region} | Type:{selected_display_types} | Cats:{sel_cats} | Grps:{sel_grps}"
        if 'last_filter_state' not in st.session_state:
            st.session_state.last_filter_state = ""
        if st.session_state.last_filter_state != current_filter_state:
            log_action("FILTER_CHANGE", current_filter_state)
            st.session_state.last_filter_state = current_filter_state

        if selected_display_types:
            selected_db_values = [TYPE_MAPPING[disp] for disp in selected_display_types]
            def filter_type(val):
                tags = [t.strip() for t in str(val).split(',')]
                for sel in selected_db_values:
                    if sel in tags: return True
                return False
            filtered_df = filtered_df[filtered_df['Type'].apply(filter_type)]

        if sel_cats: filtered_df = filtered_df[filtered_df[cols['cat']].apply(lambda x: any(c in str(x) for c in sel_cats))]
        if sel_grps: filtered_df = filtered_df[filtered_df[cols['grp']].apply(lambda x: any(g in str(x) for g in sel_grps))]

        st.markdown("---")
        st.subheader(f"{txt['res']}: {len(filtered_df)}")
        
        if len(filtered_df) == 0: st.warning(txt['no_res'])
        else:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    c_img, c_txt = st.columns([1, 2])
                    with c_img:
                        name_en = clean_filename(str(row['Name_EN']))
                        img_path = os.path.join("images", f"{name_en}.jpg")
                        st.markdown(get_local_image_html(img_path, height="120px", radius="8px"), unsafe_allow_html=True)
                    with c_txt:
                        st.markdown(f"**{row[cols['name']]}**")
                        desc_text = str(row[cols['desc']])
                        if len(desc_text) > 40: desc_text = desc_text[:40] + "..."
                        st.write(f"<span style='font-size:14px; color:#666;'>{desc_text}</span>", unsafe_allow_html=True)
                        st.caption(f"📍 {row[cols['area']]} | ⏱️ {row['Deep_Time']} min")
                        if st.button(txt['dtl_btn'], key=f"btn_all_{idx}", use_container_width=True):
                            go_detail(row)
                            st.rerun()

    # [PAGE 4] 상세 페이지
    elif st.session_state.page == 'detail':
        row = st.session_state.current_place
        
        if st.button(txt['back']):
            go_back()
        
        zone_col = 'Zone'
        if 'ZONE' in df.columns: zone_col = 'ZONE'
        elif 'zone' in df.columns: zone_col = 'zone'
        current_zone = str(row.get(zone_col, ''))
        if pd.isna(current_zone) or current_zone == 'nan': current_zone = ""

        # [지도]
        if 'lat' in row and 'lon' in row:
            try:
                dest_lat, dest_lon = float(row['lat']), float(row['lon'])
                if dest_lat != 0 and dest_lon != 0:
                    m = folium.Map(location=[dest_lat, dest_lon], zoom_start=14)
                    fixed_hubs = {"난바 (Namba)": [34.6655, 135.5006], "우메다 (Umeda)": [34.7025, 135.4959], "교토역 (Kyoto St.)": [34.9858, 135.7588]}
                    for h_name, h_coords in fixed_hubs.items():
                        folium.Marker(h_coords, popup=h_name, tooltip=h_name, icon=folium.Icon(color='green', icon='home')).add_to(m)
                    
                    if current_zone:
                        nearby = df[(df[zone_col] == current_zone) & (df['Name_KR'] != row['Name_KR']) & (df['lat'] != 0)]
                        for _, p in nearby.iterrows():
                            folium.Marker([float(p['lat']), float(p['lon'])], popup=p[cols['name']], tooltip=p[cols['name']], icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)
                    
                    folium.Marker([dest_lat, dest_lon], popup=f"📍 {row[cols['name']]}", tooltip=row[cols['name']], icon=folium.Icon(color='red', icon='star')).add_to(m)
                    st.markdown(f"### 📍 Location: {row[cols['area']]} ({current_zone})")
                    
                    map_out = st_folium(
                        m, 
                        width=None, 
                        height=400, 
                        use_container_width=True,
                        returned_objects=["last_object_clicked"] 
                    )
                    
                    if map_out and map_out['last_object_clicked']:
                        c_lat, c_lng = map_out['last_object_clicked']['lat'], map_out['last_object_clicked']['lng']
                        found = df[(df['lat'].sub(c_lat).abs() < 0.0001) & (df['lon'].sub(c_lng).abs() < 0.0001)]
                        if not found.empty:
                            new_r = found.iloc[0]
                            if new_r['Name_KR'] != row['Name_KR']:
                                go_detail(new_r)
                                st.rerun()
            except: pass

        st.divider()
        col_left, col_right = st.columns([6, 4], gap="large")
        
        with col_left:
            name_en = clean_filename(str(row['Name_EN']))
            img_path = os.path.join("images", f"{name_en}.jpg")
            img_html = get_local_image_html(img_path, height="350px", radius="12px")
            
            g_img_col = 'Google_Image_KR' if language == "한국어" else 'Google_Image_EN'
            if str(row.get(g_img_col, '')).startswith('http'): 
                st.markdown(f'<a href="{row[g_img_col]}" target="_blank">{img_html}</a>', unsafe_allow_html=True)
            else: 
                st.markdown(img_html, unsafe_allow_html=True)
                
            guide_text = "클릭 시 구글 이미지 검색으로 이동합니다" if language == "한국어" else "Click to search on Google Images"
            st.caption(f"<div style='text-align: center; margin-top: -10px;'>{guide_text}</div>", unsafe_allow_html=True)
            
            st.write("")
            st.title(row[cols['name']])
            
            if language == "한국어":
                hub_name = str(row.get('Hub_KR', ''))
                time_ref = f"{hub_name} 기준" if hub_name else "기준"
            else:
                hub_name = str(row.get('Hub_EN', ''))
                time_ref = f"From {hub_name}" if hub_name else "From City Center"
                
            st.caption(f"⏱️ {time_ref} {row['Deep_Time']} min")
            
            st.markdown("#### 📝 Description")
            st.write(row[cols['desc']])
            st.write("")
            
            tags = str(row[cols['tag']]).split('#')
            st.info("   ".join([f"#{t.strip()}" for t in tags if t.strip()]))
            
            map_url = str(row.get(cols['map'], ''))
            
            if map_url.startswith('http'):
                if st.button("🗺️ Open Google Map", key="btn_google_map", use_container_width=True):
                    log_action("CLICK_MAP", f"Place: {row['Name_KR']}")
                    js_code = f"<script>window.open('{map_url}', '_blank');</script>"
                    components.html(js_code, height=0)
                    
        with col_right:
            st.subheader("🔭 Nearby Places")
            st.caption(f"Same Zone: {current_zone}")
            if current_zone: recs = df[(df[zone_col] == current_zone) & (df['Name_KR'] != row['Name_KR'])]
            else: recs = pd.DataFrame()
            if len(recs) == 0: st.write("No nearby places.")
            else:
                for _, r_row in recs.iterrows():
                    with st.container(border=True):
                        rc1, rc2 = st.columns([1, 2.5])
                        with rc1:
                            r_name_en = clean_filename(str(r_row['Name_EN']))
                            st.markdown(get_local_image_html(os.path.join("images", f"{r_name_en}.jpg"), height="70px", radius="8px"), unsafe_allow_html=True)
                        with rc2:
                            st.write(f"**{r_row[cols['name']]}**")
                            st.caption(f"{r_row[cols['cat']]}")
                            if st.button("View", key=f"rec_{r_name_en}", use_container_width=True):
                                go_detail(r_row)
                                st.rerun()
