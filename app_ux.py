import streamlit as st
import pandas as pd
import base64
import os
import folium
from streamlit_folium import st_folium

# [로그/시간] 로그 추적을 위한 라이브러리
import logging
from datetime import datetime
import pytz

# =========================================================
# 0. 로깅(Log) 설정: 사용자 행동 추적
# =========================================================
# 배포 후 'Manage app -> Logs' 메뉴에서 확인 가능한 설정입니다.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_action(action, details=""):
    """
    사용자의 행동을 서버 로그로 남기는 함수입니다.
    - action: 행동 이름 (예: VIEW_DETAIL, SEARCH_FILTER)
    - details: 상세 내용 (예: 어떤 장소를 클릭했는지)
    """
    try:
        # 한국 시간(KST) 기준으로 시간 기록
        kst = pytz.timezone('Asia/Seoul') 
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    except:
        # 시간 설정 에러 시 기본 시간 사용
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    log_msg = f"[{now}] ACTION: {action} | DETAILS: {details}"
    
    # 1. 콘솔 출력 (클라우드 로그창에 표시됨)
    print(log_msg) 
    # 2. 로거에 기록
    logger.info(log_msg)

# =========================================================
# 1. 기본 환경 설정 및 유틸리티 함수
# =========================================================
st.set_page_config(page_title="Osaka Trip Curator", layout="wide")

def clean_filename(name):
    """이미지 파일명을 찾기 위해 특수문자를 제거하는 함수"""
    return "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in name]).strip()

def get_local_image_html(file_path, height="200px", radius="12px"):
    """
    로컬(images 폴더)에 있는 이미지를 HTML 태그로 변환하는 함수
    - 둥근 모서리와 그림자 효과(CSS)가 적용되어 있습니다.
    """
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        # CSS 스타일: 크기, 둥근 모서리, 그림자, 마우스 오버 효과
        img_style = f'''
            width: 100%; 
            height: {height}; 
            object-fit: cover; 
            border-radius: {radius}; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        '''
        # 마우스 올리면 살짝 커지는 효과 (scale 1.02)
        return f'<img src="data:image/jpeg;base64,{encoded}" style="{img_style}" onmouseover="this.style.transform=\'scale(1.02)\'" onmouseout="this.style.transform=\'scale(1.0)\'">'
    else:
        # 이미지가 없을 때 회색 박스 표시
        return f'<div style="width:100%; height:{height}; background-color:#f0f0f0; border-radius:{radius}; display:flex; align-items:center; justify-content:center; color:#999;">No Image</div>'

@st.cache_data(ttl=600)
def load_data():
    """
    구글 스프레드시트에서 데이터를 불러오고 전처리하는 함수
    - ttl=600: 10분마다 데이터를 새로고침
    """
    sheet_id = "1aEKUB0EBFApDKLVRd7cMbJ6vWlR7-yf62L5MHqMGvp4"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0"
    
    try:
        df = pd.read_csv(sheet_url)
        df = df.fillna("") # 빈칸 채우기
        
        # 소요시간(Deep_Time) 숫자 변환
        if 'Deep_Time' in df.columns:
            df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
            df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
        
        # 위도/경도 컬럼명 통일 및 숫자 변환
        if '위도' in df.columns and '경도' in df.columns:
            df = df.rename(columns={'위도': 'lat', '경도': 'lon'})
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data()

# =========================================================
# 2. 세션 상태(Session State) 관리
# =========================================================
# 페이지가 새로고침되어도 변수를 기억하기 위함

if 'page' not in st.session_state:
    st.session_state.page = 'home' # 현재 페이지 (home / detail)
    #log_action("APP_START", "User entered the app") # [로그] 최초 접속 #지속적인 더미 데이터로 주석처리_삭제

if 'current_place' not in st.session_state:
    st.session_state.current_place = None # 현재 선택한 장소 정보

# 페이지 이동 함수들
def go_detail(row):
    """상세 페이지로 이동하면서 로그를 남김"""
    st.session_state.current_place = row
    st.session_state.page = 'detail'
    log_action("VIEW_DETAIL", f"Place: {row['Name_KR']} ({row['Name_EN']})")

def go_back_to_list():
    """목록으로 돌아오면서 로그를 남김"""
    st.session_state.page = 'home'
    st.session_state.current_place = None
    log_action("BACK_TO_LIST", "Returned to list view")

# =========================================================
# 3. 언어 및 UI 텍스트 설정
# =========================================================
col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    # 언어 선택 라디오 버튼
    language = st.radio("Language", ["🇰🇷 한국어", "🇺🇸 English"], horizontal=True, label_visibility="collapsed")

# 언어에 따른 텍스트 딕셔너리
if language == "🇰🇷 한국어":
    cols = {'name': 'Name_KR', 'desc': 'Description_KR', 'loc': 'Landmark_KR', 'cat': 'Category_KR', 'grp': 'Group_KR', 'tag': 'Tag_KR', 'area': 'Area_KR', 'map': 'Google_Map_KR'}
    txt = {
        'title': "🐙 오사카/교토 여행 큐레이터",
        'region_label': "🗺️ 지역 선택 (Region)",
        'regions': ["오사카 (Osaka)", "교토 (Kyoto)"],
        'type_label': "📍 어디로 갈까요? (Type)", 
        'cats': ["자연", "도시", "역사/전통", "휴식", "쇼핑"],
        'grps': ["혼자", "연인", "친구", "부모님", "어린이"],
        'btns': ["랜드마크", "시내", "시외", "근교"],
        'res': "검색 결과",
        'no_res': "조건에 맞는 장소가 없습니다.",
        'dtl_btn': "📝 상세보기",
        'back': "⬅️ 목록으로 돌아가기",
        'guide': "👆 위에서 **여행 스타일**을 선택하면 장소를 추천해드려요!"
    }
else:
    cols = {'name': 'Name_EN', 'desc': 'Description_EN', 'loc': 'Landmark_EN', 'cat': 'Category_EN', 'grp': 'Group_EN', 'tag': 'Tag_EN', 'area': 'Area_EN', 'map': 'Google_Map_EN'}
    txt = {
        'title': "🐙 Osaka/Kyoto Travel Curator",
        'region_label': "🗺️ Region",
        'regions': ["Osaka", "Kyoto"],
        'type_label': "📍 Where do you want to go?",
        'cats': ["Nature", "City", "History/Culture", "Relax", "Shopping"],
        'grps': ["Solo", "Couple", "Friends", "Parents", "Kids"],
        'btns': ["Landmark", "Downtown", "Outskirts", "Side Trips"],
        'res': "Results",
        'no_res': "No places found.",
        'dtl_btn': "📝 View Details",
        'back': "⬅️ Back to List",
        'guide': "👆 Please select a **travel style** above to see recommendations!"
    }

if st.session_state.page == 'home':
    st.title(txt['title'])

# =========================================================
# 4. 화면 라우팅 (페이지 분기)
# =========================================================

# ---------------------------------------------------------
# [PAGE 1] 홈 & 리스트 화면
# ---------------------------------------------------------
if st.session_state.page == 'home':
    
    # [입력] 상단 필터 영역 (컨테이너로 묶음)
    with st.container():
        st.write(f"**{txt['region_label']}**")
        selected_region = st.radio("Region", txt['regions'], horizontal=True, label_visibility="collapsed")
        st.write("") 

        st.write(f"**{txt['type_label']}**")
        selected_type = st.pills("Type", txt['btns'], selection_mode="multi", default=[], label_visibility="collapsed")
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.write("🏷️ **Category**")
            sel_cats = st.pills("Cats", txt['cats'], selection_mode="multi", label_visibility="collapsed")
        with c2:
            st.write("👥 **Group**")
            sel_grps = st.pills("Grps", txt['grps'], selection_mode="multi", label_visibility="collapsed")
        st.divider()

    # ---------------------------------------------------------------------------
    # [핵심] 필터 로그 기록 (조건 변경 즉시 기록)
    # ---------------------------------------------------------------------------
    # 현재 사용자가 선택한 모든 조건을 하나의 문자열로 만듭니다.
    # [로그] 필터 변경 기록 (의미 있는 클릭만 남기기)
    current_state_str = f"Region:{selected_region} | Type:{selected_type} | Cats:{sel_cats} | Grps:{sel_grps}"
    
    if 'last_filter_state' not in st.session_state:
        st.session_state.last_filter_state = ""
    
    # 직전 상태와 현재 상태가 다르면 로직 진입
    if st.session_state.last_filter_state != current_state_str:
        st.session_state.last_filter_state = current_state_str
        
        # ⭐ 사용자가 'Type'을 최소 하나라도 선택했을 때만 로그를 기록합니다.
        # 서버의 자동 상태 점검(Health Check)은 Type이 비어있으므로 무시됩니다.
        if selected_type: 
            log_action("FILTER_CHANGE", current_state_str)

    # ---------------------------------------------------------------------------

    # [출력] 리스트 보여주기 로직
    if not selected_type:
        st.info(txt['guide']) # 타입을 선택하지 않았을 때 안내문
    else:
        # 1. 데이터 필터링 시작
        filtered_df = df.copy()
        target_col_loc = 'Landmark_KR' if language == "🇰🇷 한국어" else 'Landmark_EN'
        
        # (1) 지역 필터 (Hub 기준: 오사카=난바/우메다, 교토=교토/기온)
        is_kyoto = (selected_region == txt['regions'][1])
        if is_kyoto:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('교토|기온', na=False)]
        else:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('난바|우메다', na=False)]
            
        # (2) 타입 필터 (선택한 모든 타입 포함)
        if selected_type:
            filtered_df = filtered_df[filtered_df[target_col_loc].isin(selected_type)]

        # (3) 카테고리 & 그룹 다중 선택 필터
        if sel_cats:
            filtered_df = filtered_df[filtered_df[cols['cat']].apply(lambda x: any(c in str(x) for c in sel_cats))]
        if sel_grps:
            filtered_df = filtered_df[filtered_df[cols['grp']].apply(lambda x: any(g in str(x) for g in sel_grps))]

        # 결과 개수 표시
        st.subheader(f"{txt['res']}: {len(filtered_df)}")

        # 결과가 없을 때
        if len(filtered_df) == 0:
            st.warning(txt['no_res'])
        else:
            # 갤러리 뷰 (3열 그리드)
            num_columns = 3
            rows = [filtered_df.iloc[i:i + num_columns] for i in range(0, len(filtered_df), num_columns)]

            for row_data in rows:
                cols_grid = st.columns(num_columns)
                for col, (_, row) in zip(cols_grid, row_data.iterrows()):
                    with col:
                        # 이미지 로드
                        name_en = clean_filename(str(row['Name_EN']))
                        img_path = os.path.join("images", f"{name_en}.jpg")
                        st.markdown(get_local_image_html(img_path, height="200px"), unsafe_allow_html=True)
                        
                        # 장소 이름 및 지역
                        st.write(f"**{row[cols['name']]}**")
                        st.caption(f"📍 {row[cols['area']]}")
                        
                        # 상세보기 버튼 (클릭 시 go_detail 함수 실행)
                        st.button(
                            txt['dtl_btn'], 
                            key=f"btn_{name_en}", 
                            on_click=go_detail, 
                            args=(row,),
                            use_container_width=True
                        )

# ==========================================
# [PAGE 2] 상세 페이지 (지도 클릭 기능 추가됨!)
# ==========================================
elif st.session_state.page == 'detail':
    row = st.session_state.current_place # 현재 선택된 장소 데이터
    
    # 상단 '뒤로가기' 버튼
    if st.button(txt['back']):
        go_back_to_list()
        st.rerun()
    
    # Zone(구역) 컬럼 이름 방어 로직
    zone_col = 'Zone'
    if 'ZONE' in df.columns: zone_col = 'ZONE'
    elif 'zone' in df.columns: zone_col = 'zone'
    
    current_zone = str(row.get(zone_col, ''))
    if pd.isna(current_zone) or current_zone == 'nan': current_zone = ""

    # -----------------------------------------------------
    # 2. [Top] 지도 표시 (Interactive Map)
    # -----------------------------------------------------
    has_map_data = False
    if 'lat' in row and 'lon' in row:
        try:
            dest_lat = float(row['lat'])
            dest_lon = float(row['lon'])
            
            if dest_lat != 0 and dest_lon != 0:
                has_map_data = True
                
                # 지도 생성
                m = folium.Map(location=[dest_lat, dest_lon], zoom_start=14)
                
                # (1) [Fixed] 주요 거점 3곳 (초록색 집)
                fixed_hubs = {
                    "난바 (Namba)": [34.6655, 135.5006],
                    "우메다 (Umeda)": [34.7025, 135.4959],
                    "교토역 (Kyoto St.)": [34.9858, 135.7588]
                }
                for hub_name, hub_coords in fixed_hubs.items():
                    folium.Marker(
                        hub_coords,
                        popup=hub_name,
                        tooltip=hub_name,
                        icon=folium.Icon(color='green', icon='home') 
                    ).add_to(m)

                # (2) [Neighbors] 같은 구역 주변 장소 (파란색 i)
                if current_zone:
                    nearby_places = df[
                        (df[zone_col] == current_zone) & 
                        (df['Name_KR'] != row['Name_KR']) & 
                        (df['lat'] != 0) & (df['lon'] != 0)
                    ]
                    for _, place in nearby_places.iterrows():
                        try:
                            folium.Marker(
                                [float(place['lat']), float(place['lon'])],
                                popup=f"{place[cols['name']]}",
                                tooltip=place[cols['name']],
                                icon=folium.Icon(color='blue', icon='info-sign')
                            ).add_to(m)
                        except: continue

                # (3) [Main] 현재 장소 (빨간색 별)
                folium.Marker(
                    [dest_lat, dest_lon],
                    popup=f"📍 {row[cols['name']]} (Here!)",
                    tooltip=row[cols['name']],
                    icon=folium.Icon(color='red', icon='star')
                ).add_to(m)

                # -----------------------------------------------------------------
                # [핵심] 지도 출력 및 클릭 이벤트 수신
                # -----------------------------------------------------------------
                zone_msg = f"({current_zone})" if current_zone else ""
                st.markdown(f"### 📍 Location: {row[cols['area']]} {zone_msg}")
                
                # 지도를 변수에 담습니다 (클릭 정보를 받기 위함)
                map_output = st_folium(m, width=None, height=400, use_container_width=True)

                # [지도 클릭 로직] 만약 지도에서 무언가 클릭되었다면?
                if map_output and map_output['last_object_clicked']:
                    clicked_lat = map_output['last_object_clicked']['lat']
                    clicked_lng = map_output['last_object_clicked']['lng']
                    
                    # 1. 클릭한 좌표가 우리 데이터(df)에 있는지 찾습니다. (오차 범위 미세 허용)
                    # (실수형 좌표 비교라 정확히 일치하지 않을 수 있어 약간의 반올림 처리 등을 고려하지만, Folium은 보통 정확히 줍니다)
                    found_place = df[
                        (df['lat'].sub(clicked_lat).abs() < 0.0001) & 
                        (df['lon'].sub(clicked_lng).abs() < 0.0001)
                    ]
                    
                    # 2. 데이터가 있고, 현재 보고 있는 장소가 아니라면 -> 이동!
                    if not found_place.empty:
                        new_place_row = found_place.iloc[0]
                        if new_place_row['Name_KR'] != row['Name_KR']:
                            go_detail(new_place_row) # 상세페이지 이동 및 로그 기록
                            st.rerun() # 화면 새로고침

        except Exception as e:
            # st.error(f"Map Error: {e}") # 디버깅용
            pass

    # 지도와 상세 내용 구분선
    st.divider()

    # -----------------------------------------------------
    # 3. [Bottom] 상세 정보(좌) + 추천 리스트(우)
    # -----------------------------------------------------
    col_left, col_right = st.columns([6, 4], gap="large")
    
    # [왼쪽] 상세 정보 영역
    with col_left:
        # 이미지 불러오기
        name_en = clean_filename(str(row['Name_EN']))
        img_path = os.path.join("images", f"{name_en}.jpg")
        img_html = get_local_image_html(img_path, height="350px", radius="12px")
        
        # 구글 이미지 검색 링크
        g_img_col = 'Google_Image_KR' if language == "🇰🇷 한국어" else 'Google_Image_EN'
        google_img_url = row.get(g_img_col, '#')
        
        if str(google_img_url).startswith('http'):
            linked_img_html = f'<a href="{google_img_url}" target="_blank">{img_html}</a>'
            st.markdown(linked_img_html, unsafe_allow_html=True)
        else:
            st.markdown(img_html, unsafe_allow_html=True)
        
        st.write("")
        st.title(row[cols['name']])
        st.caption(f"⏱️ 소요시간: 약 {row['Deep_Time']}분 (Duration)")
        
        st.markdown("#### 📝 Description")
        st.write(row[cols['desc']])
        
        note_msg = "* 이미지를 클릭하면 더 많은 사진을 볼 수 있습니다." if language == "🇰🇷 한국어" else "* Click the image to see more photos on Google."
        st.caption(f"ℹ️ {note_msg}")
        
        st.write("")
        tags = str(row[cols['tag']]).split('#')
        st.info("   ".join([f"#{t.strip()}" for t in tags if t.strip()]))
        
        map_link = row.get(cols['map'], '')
        if str(map_link).startswith('http'):
            st.link_button("🗺️ Open Google Map (App)", map_link, use_container_width=True)

    # [오른쪽] 추천 리스트
    with col_right:
        st.subheader("🔭 Nearby Places")
        st.caption(f"Same Zone: {current_zone}")
        
        if current_zone:
            recs = df[(df[zone_col] == current_zone) & (df['Name_KR'] != row['Name_KR'])]
        else:
            recs = pd.DataFrame()
        
        if len(recs) == 0:
            st.write("📌 같은 구역에 등록된 다른 장소가 없습니다.")
        else:
            for _, rec_row in recs.iterrows():
                with st.container(border=True):
                    rc1, rc2 = st.columns([1, 2.5])
                    with rc1:
                        rec_name_en = clean_filename(str(rec_row['Name_EN']))
                        rec_img_path = os.path.join("images", f"{rec_name_en}.jpg")
                        st.markdown(get_local_image_html(rec_img_path, height="70px", radius="8px"), unsafe_allow_html=True)
                    with rc2:
                        st.write(f"**{rec_row[cols['name']]}**")
                        st.caption(f"{rec_row[cols['cat']]}")
                        if st.button("View", key=f"rec_{rec_name_en}", use_container_width=True):
                            go_detail(rec_row)
                            st.rerun()
