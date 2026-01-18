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

# =========================================================
# [1] 기본 설정 및 로그 (구글 시트 저장 기능 포함)
# =========================================================
import logging
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import os
import base64
import pandas as pd
import random

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. 구글 시트 연결 권한 얻기 (캐싱 적용)
@st.cache_resource
def get_google_sheet_connection():
    try:
        # Secrets에 키가 있는지 확인
        if "gcp_service_account" not in st.secrets: 
            return None
            
        secrets = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

# 2. 실제로 시트에 저장하는 함수
def save_log_to_sheet(log_data):
    try:
        client = get_google_sheet_connection()
        if client:
            # 가이드님의 구글 스프레드시트 ID
            sheet_id = "1aEKUB0EBFApDKLVRd7cMbJ6vWlR7-yf62L5MHqMGvp4" 
            spreadsheet = client.open_by_key(sheet_id)
            
            # [수정 포인트] 가이드님이 만든 탭 이름 "Logs_ai"로 변경!
            # 주의: 엑셀 하단 탭 이름이 정확히 Logs_ai 여야 합니다.
            worksheet = spreadsheet.worksheet("Logs_ai")
            
            # 데이터 한 줄 추가
            worksheet.append_row(log_data)
            print(f"✅ 저장 성공: {log_data}") 
    except Exception as e:
        # 에러 나면 콘솔에만 출력 (앱 멈춤 방지)
        print(f"❌ 저장 실패: {e}")
        pass 

# 3. 앱 전체에서 사용할 로그 함수
def log_action(action, details=""):
    try:
        kst = pytz.timezone('Asia/Seoul') 
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    except:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 사용자 ID 가져오기 (없으면 unknown)
    visitor_id = st.session_state.get('visitor_id', 'unknown')
    
    # 콘솔에 출력 (확인용)
    print(f"[{now}] {visitor_id} - {action}: {details}")
    
    # [핵심] 구글 시트로 전송!
    save_log_to_sheet([now, visitor_id, action, details])

# =========================================================
# [2] 데이터 로드
# =========================================================
st.set_page_config(page_title="Travel Curator", layout="wide")

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

# =========================================================
# [3] 세션 상태 & 화면 이동
# =========================================================
if 'visitor_id' not in st.session_state:
    st.session_state.visitor_id = st.query_params.get("id", "anonymous")
    log_action("ENTER_APP", "User accessed the app")

if 'page' not in st.session_state: st.session_state.page = 'survey'
if 'previous_page' not in st.session_state: st.session_state.previous_page = 'survey'

if 'current_place' not in st.session_state: st.session_state.current_place = None
if 'user_type' not in st.session_state: st.session_state.user_type = 0
if 'current_region' not in st.session_state: st.session_state.current_region = "오사카"

if 'survey_step' not in st.session_state: st.session_state.survey_step = 1
if 'survey_answers' not in st.session_state: st.session_state.survey_answers = {'q1': None, 'q2': None}
if 'swap_q1' not in st.session_state: st.session_state.swap_q1 = random.choice([True, False])
if 'swap_q2' not in st.session_state: st.session_state.swap_q2 = random.choice([True, False])

# --- 이동 함수 ---
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
    st.rerun()

def go_retake_survey():
    st.session_state.page = 'survey'
    st.session_state.user_type = 0
    st.session_state.survey_step = 1 
    st.session_state.survey_answers = {'q1': None, 'q2': None}
    st.session_state.swap_q1 = random.choice([True, False])
    st.session_state.swap_q2 = random.choice([True, False])
    st.rerun()

# =========================================================
# [4] 텍스트 설정 & DB 매핑
# =========================================================

TYPE_MAPPING = {
    "여행자 타입": "근랜드",
    "낭만가 타입": "원랜드",
    "탐험가 타입": "모험",
    "사색가 타입": "조용"
}
REVERSE_TYPE_MAPPING = {v: k for k, v in TYPE_MAPPING.items()}

col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    language = st.radio("Language", ["English", "한국어"], horizontal=True, label_visibility="collapsed")

if language == "한국어":
    cols = {'name': 'Name_KR', 'desc': 'Description_KR', 'loc': 'Landmark_KR', 'cat': 'Category_KR', 'grp': 'Group_KR', 'tag': 'Tag_KR', 'area': 'Area_KR', 'map': 'Google_Map_KR'}
    txt = {
        'title': "오사카/교토 여행지 리스트", 
        'survey_title': "여행에서 더 끌리는 곳",
        
        # [수정] 아래 버튼 클릭 삭제
        'survey_sub': "", 
        
        'q1_landmark': "사람은 많아도, 랜드마크", 
        'q1_local': "덜 유명해도, 로컬 스팟",
        
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
        'go_all': "전체 장소",

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
        
        'q1_landmark': "Famous Landmarks", 
        'q1_local': "Hidden Local Spots", 
        
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

# =========================================================
# [오류 방지] 현재 설정된 지역 이름이 유효한지 체크
# =========================================================
if st.session_state.current_region not in txt['regions']:
    st.session_state.current_region = txt['regions'][0]

# =========================================================
# [PAGE 1] 설문조사
# =========================================================
if st.session_state.page == 'survey':
    
    st.write(f"**{txt['region_label']}**")
    st.session_state.current_region = st.radio(
        "Region_Survey", 
        txt['regions'], 
        index=txt['regions'].index(st.session_state.current_region), 
        horizontal=True, 
        label_visibility="collapsed"
    )
    st.divider()

    # 1단계일 때만 퀵 필터 노출
    if st.session_state.survey_step == 1:
        qc1, qc2, qc3, qc4 = st.columns(4)
        if qc1.button(txt['btns'][0], use_container_width=True): go_page_recommendation(TYPE_MAPPING[txt['btns'][0]])
        if qc2.button(txt['btns'][1], use_container_width=True): go_page_recommendation(TYPE_MAPPING[txt['btns'][1]])
        if qc3.button(txt['btns'][2], use_container_width=True): go_page_recommendation(TYPE_MAPPING[txt['btns'][2]])
        if qc4.button(txt['btns'][3], use_container_width=True): go_page_recommendation(TYPE_MAPPING[txt['btns'][3]])
        st.markdown("---")

    if "Kyoto" in st.session_state.current_region or "교토" in st.session_state.current_region:
        region_tag = "kyoto"
    else:
        region_tag = "osaka"

    def get_img_path(base_name):
        return os.path.join("images", f"{base_name}_{region_tag}.jpg")

    # 제목 변경 로직
    current_title = txt['survey_title']
    if st.session_state.survey_step == 2:
        if st.session_state.survey_answers['q1'] == 'landmark':
            current_title = txt['q2b_title']
        elif st.session_state.survey_answers['q1'] == 'local':
            current_title = txt['q2a_title']

    st.subheader(current_title)
    # [수정] 서브타이틀(클릭하세요) 삭제됨

    IMG_HEIGHT = "250px"

    # [수정] 버튼 렌더링 함수: 텍스트를 버튼 안으로 통합
    def render_option(img_key, txt_key, val):
        # 1. 이미지 표시
        st.markdown(get_local_image_html(get_img_path(img_key), height=IMG_HEIGHT), unsafe_allow_html=True)
        # 2. 버튼 표시 (버튼 이름 = 설명 텍스트)
        # 텍스트 설명(st.markdown)을 삭제하고, 버튼에 txt[txt_key]를 바로 넣었습니다.
        if st.button(txt[txt_key], key=f"btn_{img_key}", use_container_width=True):
            if st.session_state.survey_step == 1:
                st.session_state.survey_answers['q1'] = val
                st.session_state.survey_step = 2
                st.rerun()
            else:
                go_page_recommendation(val)

    # Step 1
    if st.session_state.survey_step == 1:
        col1, col2 = st.columns(2)
        opt_a = ("q1_landmark", "q1_landmark", "landmark")
        opt_b = ("q1_local", "q1_local", "local")
        
        if st.session_state.swap_q1: left, right = opt_b, opt_a
        else: left, right = opt_a, opt_b
            
        with col1: render_option(*left)
        with col2: render_option(*right)

    # Step 2
    elif st.session_state.survey_step == 2:
        if st.button(f"⬅️ {txt['back']}"): 
            st.session_state.survey_step = 1
            st.rerun()
            
        col3, col4 = st.columns(2)
        
        if st.session_state.survey_answers['q1'] == 'landmark':
            opt_a = ("q2b_crowded", "q2b_crowded", "근랜드") 
            opt_b = ("q2b_far", "q2b_far", "원랜드")         
            if st.session_state.swap_q2: left, right = opt_b, opt_a
            else: left, right = opt_a, opt_b
            with col3: render_option(*left)
            with col4: render_option(*right)

        elif st.session_state.survey_answers['q1'] == 'local':
            opt_a = ("q2a_adventure", "q2a_adventure", "모험") 
            opt_b = ("q2a_quite", "q2a_quiet", "조용")         
            if st.session_state.swap_q2: left, right = opt_b, opt_a
            else: left, right = opt_a, opt_b
            with col3: render_option(*left)
            with col4: render_option(*right)

    st.divider()
    if st.button(txt['go_all'], type="secondary", use_container_width=True):
        go_page_all_places()

# =========================================================
# [PAGE 2] 추천 결과
# =========================================================
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
    
    # 멘트 가져오기
    custom_message = txt['type_messages'].get(user_result_db, "")
    
    # [수정 완료] '성향에 맞는 장소 추천 :' 삭제하고 핵심 문구만 출력
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

# =========================================================
# [PAGE 3] 전체 장소 리스트
# =========================================================
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

# =========================================================
# [PAGE 4] 상세 페이지
# =========================================================
elif st.session_state.page == 'detail':
    row = st.session_state.current_place
    
    if st.button(txt['back']):
        go_back()
    
    zone_col = 'Zone'
    if 'ZONE' in df.columns: zone_col = 'ZONE'
    elif 'zone' in df.columns: zone_col = 'zone'
    current_zone = str(row.get(zone_col, ''))
    if pd.isna(current_zone) or current_zone == 'nan': current_zone = ""

    # [지도 로직은 그대로 유지]
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
                
                map_out = st_folium(m, width=None, height=400, use_container_width=True)
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
        # 1. 이미지 표시
        name_en = clean_filename(str(row['Name_EN']))
        img_path = os.path.join("images", f"{name_en}.jpg")
        img_html = get_local_image_html(img_path, height="350px", radius="12px")
        
        g_img_col = 'Google_Image_KR' if language == "한국어" else 'Google_Image_EN'
        
        # 링크가 있으면 링크 걸기
        if str(row.get(g_img_col, '')).startswith('http'): 
            st.markdown(f'<a href="{row[g_img_col]}" target="_blank">{img_html}</a>', unsafe_allow_html=True)
        else: 
            st.markdown(img_html, unsafe_allow_html=True)
            
        # [추가 1] 이미지 하단 안내 멘트
        guide_text = "클릭 시 구글 이미지 검색으로 이동합니다" if language == "한국어" else "Click to search on Google Images"
        st.caption(f"<div style='text-align: center; margin-top: -10px;'>{guide_text}</div>", unsafe_allow_html=True)
        
        st.write("")
        st.title(row[cols['name']])
        
        # [수정 2] DB의 Hub 컬럼을 기준으로 시간 표시
        if language == "한국어":
            # 한국어일 땐 Hub_KR 사용 (예: "난바", "우메다")
            hub_name = str(row.get('Hub_KR', ''))
            time_ref = f"{hub_name} 기준" if hub_name else "기준"
        else:
            # 영어일 땐 Hub_EN 사용 (예: "Namba", "Umeda")
            hub_name = str(row.get('Hub_EN', ''))
            time_ref = f"From {hub_name}" if hub_name else "From City Center"
            
        st.caption(f"⏱️ {time_ref} {row['Deep_Time']} min")
        
        st.markdown("#### 📝 Description")
        st.write(row[cols['desc']])
        st.write("")
        tags = str(row[cols['tag']]).split('#')
        st.info("   ".join([f"#{t.strip()}" for t in tags if t.strip()]))
        if str(row.get(cols['map'], '')).startswith('http'): st.link_button("🗺️ Open Google Map", row[cols['map']], use_container_width=True)

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
