import streamlit as st
import pandas as pd
import base64
import os
import folium
from streamlit_folium import st_folium

# [추가] 로그 및 시간 관련 라이브러리
import logging
from datetime import datetime
import pytz

# ---------------------------------------------------------
# 0. 로깅 설정 (Log Tracking)
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_action(action, details=""):
    """사용자 행동을 로그로 남기는 함수"""
    try:
        kst = pytz.timezone('Asia/Seoul') 
        now = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    except:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # pytz 에러 시 기본 시간
        
    log_msg = f"[{now}] ACTION: {action} | DETAILS: {details}"
    
    # 콘솔 출력 (Streamlit Cloud Logs에서 확인 가능)
    print(log_msg) 
    logger.info(log_msg)

# ---------------------------------------------------------
# 1. 환경 설정 및 함수 정의
# ---------------------------------------------------------
st.set_page_config(page_title="Osaka Trip Curator", layout="wide")

def clean_filename(name):
    return "".join([c if c.isalnum() or c in (' ', '_', '-') else '' for c in name]).strip()

def get_local_image_html(file_path, height="200px", radius="12px"):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        img_style = f'''
            width: 100%; 
            height: {height}; 
            object-fit: cover; 
            border-radius: {radius}; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        '''
        return f'<img src="data:image/jpeg;base64,{encoded}" style="{img_style}" onmouseover="this.style.transform=\'scale(1.02)\'" onmouseout="this.style.transform=\'scale(1.0)\'">'
    else:
        return f'<div style="width:100%; height:{height}; background-color:#f0f0f0; border-radius:{radius}; display:flex; align-items:center; justify-content:center; color:#999;">No Image</div>'

@st.cache_data(ttl=600)
def load_data():
    sheet_id = "1aEKUB0EBFApDKLVRd7cMbJ6vWlR7-yf62L5MHqMGvp4"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid=0"
    
    try:
        df = pd.read_csv(sheet_url)
        df = df.fillna("")
        
        if 'Deep_Time' in df.columns:
            df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
            df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
        
        if '위도' in df.columns and '경도' in df.columns:
            df = df.rename(columns={'위도': 'lat', '경도': 'lon'})
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df = load_data()

# ---------------------------------------------------------
# 2. 세션 상태 관리
# ---------------------------------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'home'
    log_action("APP_START", "User entered the app")

if 'current_place' not in st.session_state:
    st.session_state.current_place = None

def go_detail(row):
    st.session_state.current_place = row
    st.session_state.page = 'detail'
    log_action("VIEW_DETAIL", f"Place: {row['Name_KR']} ({row['Name_EN']})")

def go_back_to_list():
    st.session_state.page = 'home'
    st.session_state.current_place = None
    log_action("BACK_TO_LIST", "Returned to list view")

# ---------------------------------------------------------
# 3. UI 텍스트 설정
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([8, 2])
with col_h2:
    language = st.radio("Language", ["🇰🇷 한국어", "🇺🇸 English"], horizontal=True, label_visibility="collapsed")

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

# ---------------------------------------------------------
# 4. 화면 라우팅
# ---------------------------------------------------------

# ==========================================
# [PAGE 1] 홈 & 리스트
# ==========================================
if st.session_state.page == 'home':
    
    # --- 상단 필터 영역 ---
    with st.container():
        st.write(f"**{txt['region_label']}**")
        selected_region = st.radio("Region", txt['regions'], horizontal=True, label_visibility="collapsed")
        st.write("") 

        st.write(f"**{txt['type_label']}**")
        selected_type = st.pills("Type", txt['btns'], selection_mode="single", default=None, label_visibility="collapsed")
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.write("🏷️ **Category**")
            sel_cats = st.pills("Cats", txt['cats'], selection_mode="multi", label_visibility="collapsed")
        with c2:
            st.write("👥 **Group**")
            sel_grps = st.pills("Grps", txt['grps'], selection_mode="multi", label_visibility="collapsed")
        st.divider()

    # --- 리스트 출력 로직 ---
    if not selected_type:
        st.info(txt['guide'])
    else:
        # 필터링
        filtered_df = df.copy()
        target_col_loc = 'Landmark_KR' if language == "🇰🇷 한국어" else 'Landmark_EN'
        
        # 지역 필터 (Hub 기준)
        is_kyoto = (selected_region == txt['regions'][1])
        if is_kyoto:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('교토|기온', na=False)]
        else:
            filtered_df = filtered_df[filtered_df['Hub_KR'].astype(str).str.contains('난바|우메다', na=False)]
            
        filtered_df = filtered_df[filtered_df[target_col_loc] == selected_type]

        if sel_cats:
            filtered_df = filtered_df[filtered_df[cols['cat']].apply(lambda x: any(c in str(x) for c in sel_cats))]
        if sel_grps:
            filtered_df = filtered_df[filtered_df[cols['grp']].apply(lambda x: any(g in str(x) for g in sel_grps))]

        # [로그] 필터링 결과 수 기록
        if 'last_filter_count' not in st.session_state or st.session_state.last_filter_count != len(filtered_df):
            st.session_state.last_filter_count = len(filtered_df)
            log_msg = f"Region:{selected_region}, Type:{selected_type}, Cats:{sel_cats} -> Result:{len(filtered_df)}"
            log_action("SEARCH_FILTER", log_msg)

        st.subheader(f"{txt['res']}: {len(filtered_df)}")

        if len(filtered_df) == 0:
            st.warning(txt['no_res'])
        else:
            num_columns = 3
            rows = [filtered_df.iloc[i:i + num_columns] for i in range(0, len(filtered_df), num_columns)]

            for row_data in rows:
                cols_grid = st.columns(num_columns)
                for col, (_, row) in zip(cols_grid, row_data.iterrows()):
                    with col:
                        name_en = clean_filename(str(row['Name_EN']))
                        img_path = os.path.join("images", f"{name_en}.jpg")
                        st.markdown(get_local_image_html(img_path, height="200px"), unsafe_allow_html=True)
                        
                        st.write(f"**{row[cols['name']]}**")
                        st.caption(f"📍 {row[cols['area']]}")
                        
                        st.button(
                            txt['dtl_btn'], 
                            key=f"btn_{name_en}", 
                            on_click=go_detail, 
                            args=(row,),
                            use_container_width=True
                        )

# ==========================================
# [PAGE 2] 상세 페이지
# ==========================================
elif st.session_state.page == 'detail':
    row = st.session_state.current_place
    
    # 1. 상단 네비게이션
    if st.button(txt['back']):
        go_back_to_list()
        st.rerun()
    
    # Zone 컬럼명 방어 로직
    zone_col = 'Zone'
    if 'ZONE' in df.columns: zone_col = 'ZONE'
    elif 'zone' in df.columns: zone_col = 'zone'
    
    current_zone = str(row.get(zone_col, ''))
    if pd.isna(current_zone) or current_zone == 'nan':
        current_zone = ""

    # -----------------------------------------------------
    # 2. [Top] 지도 표시 (3종류 핀 + 교토역 + 초록색)
    # -----------------------------------------------------
    has_map_data = False
    if 'lat' in row and 'lon' in row:
        try:
            dest_lat = float(row['lat'])
            dest_lon = float(row['lon'])
            
            if dest_lat != 0 and dest_lon != 0:
                has_map_data = True
                
                m = folium.Map(location=[dest_lat, dest_lon], zoom_start=14)
                
                # (1) [Fixed] 난바/우메다/교토역 (초록색 집)
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
                        icon=folium.Icon(color='green', icon='home') # 초록색
                    ).add_to(m)

                # (2) [Neighbors] 같은 Zone 장소 (파란색 정보)
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
                        except:
                            continue

                # (3) [Main] 현재 선택 장소 (빨간색 별)
                folium.Marker(
                    [dest_lat, dest_lon],
                    popup=f"📍 {row[cols['name']]} (Here!)",
                    tooltip=row[cols['name']],
                    icon=folium.Icon(color='red', icon='star')
                ).add_to(m)

                zone_msg = f"({current_zone})" if current_zone else ""
                st.markdown(f"### 📍 Location: {row[cols['area']]} {zone_msg}")
                st_folium(m, width=None, height=400, use_container_width=True)
                
        except Exception:
            pass

    st.divider()

    # -----------------------------------------------------
    # 3. [Bottom] 상세 정보(좌) + 추천 리스트(우)
    # -----------------------------------------------------
    col_left, col_right = st.columns([6, 4], gap="large")
    
    # [왼쪽] 상세 정보
    with col_left:
        # 이미지 (클릭 시 구글 링크)
        name_en = clean_filename(str(row['Name_EN']))
        img_path = os.path.join("images", f"{name_en}.jpg")
        img_html = get_local_image_html(img_path, height="350px", radius="12px")
        
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

    # [오른쪽] 같은 Zone 추천 리스트
    with col_right:
        st.subheader("🔭 Nearby Places")
        st.caption(f"Same Zone: {current_zone}")
        
        if current_zone:
            recs = df[
                (df[zone_col] == current_zone) & 
                (df['Name_KR'] != row['Name_KR'])
            ]
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