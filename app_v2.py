import streamlit as st
import pandas as pd
import os
import base64

# ---------------------------------------------------------
# [신규 기능 함수] 클릭 가능한 로컬 이미지 HTML 생성
# ---------------------------------------------------------
def get_clickable_image_html(img_path, target_url, width="100%"):
    """
    로컬 이미지를 읽어서 base64로 인코딩한 뒤, 
    지정된 URL로 연결되는 HTML <a> 태그로 감싸서 반환합니다.
    """
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        # 이미지에 마우스를 올렸을 때 살짝 커지는 효과 추가 (CSS)
        html_code = f'''
            <a href="{target_url}" target="_blank" style="text-decoration: none;">
                <img src="data:image/jpeg;base64,{encoded}" 
                     style="width:{width}; border-radius:12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); transition: transform 0.3s ease;"
                     onmouseover="this.style.transform='scale(1.02)'"
                     onmouseout="this.style.transform='scale(1.0)'"
                >
            </a>
        '''
        return html_code
    else:
        return None

# ---------------------------------------------------------
# 0. 세션 상태 초기화
# ---------------------------------------------------------
if 'selected_tags' not in st.session_state:
    st.session_state.selected_tags = []

def toggle_tag(tag):
    if tag in st.session_state.selected_tags:
        st.session_state.selected_tags.remove(tag)
    else:
        st.session_state.selected_tags.append(tag)

# ---------------------------------------------------------
# 1. 데이터 로드
# ---------------------------------------------------------
st.set_page_config(page_title="Osaka Travel Guide Project 2", layout="wide")

# @st.cache_data # 개발 중에는 주석 처리 (배포 시 해제)
def load_data():
    try:
        # 보내주신 헤더에 맞춰 데이터 읽기
        df = pd.read_excel("data.xlsx")
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None
    
    # 필수 데이터 확인 (한국어 이름 없으면 삭제)
    if 'Name_KR' in df.columns:
        df = df.dropna(subset=['Name_KR'])
    
    # 시간 숫자 변환
    if 'Deep_Time' in df.columns:
        df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
        df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
    
    df = df.fillna("")
    return df

df = load_data()

if df is None:
    st.error("🚨 'data.xlsx' 파일을 찾을 수 없거나 읽을 수 없습니다. 파일명과 경로를 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 2. 언어 설정 및 변수 매핑 (핵심!)
# ---------------------------------------------------------
with st.sidebar:
    # 언어 선택 라디오 버튼
    language = st.radio("🌐 Language / 언어", ["🇰🇷 한국어", "🇺🇸 English"])
    st.divider()

# 언어에 따라 사용할 엑셀 컬럼명과 UI 텍스트 결정
if language == "🇰🇷 한국어":
    # [데이터 컬럼]
    col_name = 'Name_KR'
    col_desc = 'Description_KR'
    col_area = 'Area_KR'
    col_hub  = 'Hub_KR'
    col_cat  = 'Category_KR'
    col_grp  = 'Group_KR'
    col_tag  = 'Tag_KR'       # [수정 0] 한국어 태그 컬럼
    col_map  = 'Google_Map_KR'
    col_img  = 'Google_Image_KR'
    
    # [UI 텍스트]
    ui_title = "🐙 오사카/교토 여행 큐레이션 (Ver 2.0)"
    ui_hub_label = "🏨 숙소(출발지)"
    ui_hub_opts = ["난바", "우메다", "교토역"]
    ui_time_label = "⏰ 소요 시간 (중복 선택)"
    ui_time_opts = ["30분 이내", "30분~1시간", "1시간~2시간"]
    ui_theme_label = "🏷️ 테마 (Category)"
    ui_theme_opts = ["자연", "도시", "역사/전통", "휴식", "쇼핑", "문화"]
    ui_group_label = "👥 누구와? (Group)"
    ui_group_opts = ["혼자", "연인", "친구", "부모님", "어린이"]
    ui_msg_filter = "🎯 원하는 여행 스타일을 콕콕 찍어보세요!"
    ui_msg_result = "🔍 **검색 결과:** 총"
    ui_msg_no_result = "조건에 맞는 장소가 없거나, 시간을 선택하지 않으셨습니다. 😅"
    ui_expander_label = "📝 상세정보 보기 (Click)" # [수정 3] Expander 라벨
    ui_btn_map = "🗺️ 지도 보기"
    # ui_btn_img = "📸 사진 보기" # 더 이상 버튼으로 쓰지 않음
    ui_tag_info = "📢 **선택된 태그:**"
    ui_btn_reset = "🔄 태그 초기화"
    ui_img_missing = "이미지 준비중"

else: # English
    # [Data Columns]
    col_name = 'Name_EN'
    col_desc = 'Description_EN'
    col_area = 'Area_EN'
    col_hub  = 'Hub_EN'
    col_cat  = 'Category_EN'
    col_grp  = 'Group_EN'
    col_tag  = 'Tag_EN'       # [수정 0] 영어 태그 컬럼
    col_map  = 'Google_Map_EN'
    col_img  = 'Google_Image_EN'
    
    # [UI Text]
    ui_title = "🐙 Osaka/Kyoto Travel Guide (Ver 2.0)"
    ui_hub_label = "🏨 Your Hotel (Hub)"
    ui_hub_opts = ["Namba", "Umeda", "Kyoto Station"]
    ui_time_label = "⏰ Travel Time (Multi-select)"
    ui_time_opts = ["Within 30 min", "30~60 min", "1~2 hours"]
    ui_theme_label = "🏷️ Theme (Category)"
    ui_theme_opts = ["Nature", "City", "History/Culture", "Relax", "Shopping"]
    ui_group_label = "👥 With whom? (Group)"
    ui_group_opts = ["Solo", "Couple", "Friends", "Parents", "Kids"]
    ui_msg_filter = "🎯 Select your travel style!"
    ui_msg_result = "🔍 **Results:** Total"
    ui_msg_no_result = "No places found matching your criteria. 😅"
    ui_expander_label = "📝 View Details (Click)" # [수정 3] Expander Label
    ui_btn_map = "🗺️ Google Map"
    # ui_btn_img = "📸 Gallery" # No longer used as button
    ui_tag_info = "📢 **Selected Tags:**"
    ui_btn_reset = "🔄 Reset Tags"
    ui_img_missing = "Image coming soon"

# ---------------------------------------------------------
# 3. 로직 함수 (시간 계산)
# ---------------------------------------------------------
def calculate_total_time(user_hub, place_hub, deep_time):
    # [간단 로직] 입력이 영어면 한글로 변환해서 계산
    hub_map = {
        "Namba": "난바", "Umeda": "우메다", "Kyoto Station": "교토역",
        "난바": "난바", "우메다": "우메다", "교토역": "교토역"
    }
    
    u_hub = hub_map.get(user_hub, user_hub)
    p_hub = hub_map.get(place_hub, place_hub)

    transit_time = 0
    if u_hub == p_hub: transit_time = 0
    elif (u_hub == "난바" and p_hub == "우메다") or (u_hub == "우메다" and p_hub == "난바"): transit_time = 20
    elif (u_hub == "우메다" and p_hub == "교토역") or (u_hub == "교토역" and p_hub == "우메다"): transit_time = 30
    elif (u_hub == "난바" and p_hub == "교토역") or (u_hub == "교토역" and p_hub == "난바"): transit_time = 50
    
    return transit_time + deep_time

# ---------------------------------------------------------
# 4. 화면 구성 (UI)
# ---------------------------------------------------------
st.title(ui_title)

# [사이드바 설정]
with st.sidebar:
    st.header("⚙️ Settings")
    
    # 숙소 선택
    user_hub = st.selectbox(ui_hub_label, ui_hub_opts)
    
    # 시간 선택
    st.subheader(ui_time_label)
    selected_times = st.pills(
        "Time",
        ui_time_opts,
        selection_mode="multi",
        default=[ui_time_opts[0], ui_time_opts[1]]
    )
    
    st.divider()
    st.caption("Designed by JSM | Ver 2.0 (Global)")

# [메인 필터]
st.write(f"### {ui_msg_filter}")

col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption(ui_theme_label)
    selected_categories = st.pills("Cat", ui_theme_opts, selection_mode="multi", key="cat_pills")

with col_f2:
    st.caption(ui_group_label)
    selected_groups = st.pills("Grp", ui_group_opts, selection_mode="multi", key="group_pills")

st.divider()

# ---------------------------------------------------------
# 5. 데이터 필터링 로직
# ---------------------------------------------------------
# 1) 시간 계산
df['Total_Time'] = df.apply(lambda row: calculate_total_time(user_hub, row[col_hub], row['Deep_Time']), axis=1)

# 2) 시간 필터
if not selected_times:
    filtered_df = pd.DataFrame(columns=df.columns)
else:
    conditions = []
    if ui_time_opts[0] in selected_times: conditions.append(df['Total_Time'] <= 30)
    if ui_time_opts[1] in selected_times: conditions.append((df['Total_Time'] > 30) & (df['Total_Time'] <= 60))
    if ui_time_opts[2] in selected_times: conditions.append((df['Total_Time'] > 60) & (df['Total_Time'] <= 120))
    
    if conditions:
        final_condition = conditions[0]
        for c in conditions[1:]: final_condition = final_condition | c
        filtered_df = df[final_condition]
    else:
        filtered_df = df

# 3) 테마 & 그룹 필터
if selected_categories:
    filtered_df = filtered_df[filtered_df[col_cat].apply(lambda x: any(cat in str(x) for cat in selected_categories))]

if selected_groups:
    filtered_df = filtered_df[filtered_df[col_grp].apply(lambda x: any(grp in str(x) for grp in selected_groups))]

# 4) 태그 필터 (언어별 태그 컬럼 사용)
# [수정 0] col_tag 변수 사용
if st.session_state.selected_tags:
    st.info(f"{ui_tag_info} {', '.join([f'#{t}' for t in st.session_state.selected_tags])}")
    
    pattern = '|'.join(st.session_state.selected_tags)
    # 언어 설정에 맞는 태그 컬럼에서 검색
    filtered_df = filtered_df[filtered_df[col_tag].str.contains(pattern, na=False)]

    if st.button(ui_btn_reset):
        st.session_state.selected_tags = []
        st.rerun()

# 정렬
filtered_df = filtered_df.sort_values('Total_Time')

# ... (이전 코드: 임포트, 데이터 로드, 사이드바 설정 등은 동일) ...

# ---------------------------------------------------------
# [추가 기능] 보기 방식 선택 (사이드바에 추가해주세요)
# ---------------------------------------------------------
with st.sidebar:
    st.divider()
    # 화면 크기에 따라 사용자가 선택할 수 있게 함
    view_mode = st.radio("👀 View Mode", ["List (1열 - Mobile)", "Gallery (3열 - PC)"], index=1)

# ... (중간 코드: 데이터 필터링 로직 동일) ...

# ---------------------------------------------------------
# ---------------------------------------------------------
# 6. 결과 출력 (수정됨)
# ---------------------------------------------------------
st.markdown(f"{ui_msg_result} **{len(filtered_df)}**")

if len(filtered_df) == 0:
    st.warning(ui_msg_no_result)
else:
    # 1. 보기 모드에 따라 열 개수 결정
    if "Gallery" in view_mode:
        num_columns = 3  # PC용 3열
    else:
        num_columns = 1  # 모바일용 1열 (리스트)

    # 2. 그리드 배치 로직
    rows = [filtered_df.iloc[i:i + num_columns] for i in range(0, len(filtered_df), num_columns)]

    for row_data in rows:
        cols = st.columns(num_columns)
        
        for col, (index, row) in zip(cols, row_data.iterrows()):
            with col:
                # --- [A] 이미지 (클릭 시 구글 이미지 이동) ---
                img_path = os.path.join("images", f"{row['Name_EN']}.jpg")
                target_link = str(row.get(col_img, '')).strip()
                
                # 이미지 표시
                if target_link.startswith('http'):
                    html_img = get_clickable_image_html(img_path, target_link)
                    if html_img:
                        st.markdown(html_img, unsafe_allow_html=True)
                    else:
                        st.warning(f"⚠️ {ui_img_missing}")
                else:
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)

                # --- [B] 핵심 정보 (이름 + 시간 + 지역) ---
                # 이름은 굵게, 나머지는 작고 회색으로 표시 (수정사항 1 반영)
                # "from X" 없이 시간과 지역만 깔끔하게 표시
                info_text = f"⏱️ {row['Total_Time']} min | 📍 {row[col_area]}"
                
                st.markdown(
                    f"""
                    <div style="margin-top: 5px; line-height: 1.2;">
                        <span style="font-size: 1.1em; font-weight: bold;">{row[col_name]}</span><br>
                        <span style="font-size: 0.85em; color: gray;">{info_text}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

                # --- [C] 태그 버튼 (클릭 시 필터링) ---
                # (수정사항 2 반영: 클릭 시 선택/해제 토글)
                tags = [t.strip() for t in str(row[col_tag]).split('#') if t.strip()]
                
                if tags:
                    st.write("") # 약간의 여백
                    # 태그 버튼들을 가로로 꽉 차게 배치하기 위해 columns 사용
                    # 공간 효율을 위해 최대 3~4개까지만 한 줄에, 넘으면 다음 줄 (Streamlit 버튼 특성상 나열이 쉽지 않아 wrap 방식 사용)
                    
                    # 태그를 감싸는 컨테이너
                    tag_cols = st.columns(len(tags) if len(tags) < 5 else 5)
                    
                    for i, tag in enumerate(tags):
                        # 너무 많으면 5개까지만 표시 (UI 깨짐 방지)하고 break 할 수도 있음. 
                        # 여기서는 row index를 활용해 줄바꿈 효과를 흉내냄
                        current_col = tag_cols[i % 5] 
                        
                        # 현재 선택된 태그인지 확인
                        is_selected = tag in st.session_state.selected_tags
                        
                        # 버튼 라벨 (선택되면 체크표시)
                        label = f"✅{tag}" if is_selected else f"#{tag}"
                        
                        # 버튼 생성 (Key를 유니크하게 만들어야 함: row인덱스 + 태그명)
                        # help="클릭하여 필터에 추가/제거"
                        current_col.button(
                            label, 
                            key=f"btn_{index}_{tag}", 
                            on_click=toggle_tag, 
                            args=(tag,),
                            use_container_width=True 
                        )

                # --- [D] 상세정보 (Expander) ---
                with st.expander(ui_expander_label):
                    st.write(row[col_desc])
                    
                    # 지도 버튼 (Expander 안으로 이동)
                    st.divider()
                    map_link = str(row.get(col_map, '')).strip()
                    if map_link.startswith('http'):
                        st.link_button(ui_btn_map, map_link, use_container_width=True)
                    else:
                        st.button(ui_btn_map, disabled=True, key=f"map_dis_{index}", use_container_width=True)
                
                # 카드 간 간격
                st.write("---")
                
                    #streamlit run app_v2.py