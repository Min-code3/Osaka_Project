import streamlit as st
import pandas as pd

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
st.set_page_config(page_title="Osaka Travel Guide", layout="wide")

# @st.cache_data # 개발 중에는 주석 처리 (배포 시 해제)
def load_data():
    try:
        # 보내주신 헤더에 맞춰 데이터 읽기
        df = pd.read_excel("data.xlsx")
    except:
        return None
    
    # 필수 데이터 확인 (한국어 이름 없으면 삭제)
    df = df.dropna(subset=['Name_KR'])
    
    # 시간 숫자 변환
    if 'Deep_Time' in df.columns:
        df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
        df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
    
    df = df.fillna("")
    return df

df = load_data()

if df is None:
    st.error("🚨 '오사카 데이터.xlsx' 파일을 찾을 수 없습니다.")
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
    col_map  = 'Google_Map_KR'
    col_img  = 'Google_Image_KR'
    
    # [UI 텍스트]
    ui_title = "🐙 오사카/교토 여행 큐레이션"
    ui_hub_label = "🏨 숙소(출발지)"
    ui_hub_opts = ["난바", "우메다", "교토역"] # Hub_KR 데이터와 일치해야 함
    ui_time_label = "⏰ 소요 시간 (중복 선택)"
    ui_time_opts = ["30분 이내", "30분~1시간", "1시간~2시간"]
    ui_theme_label = "🏷️ 테마 (Category)"
    ui_theme_opts = ["자연", "도시", "역사/전통", "휴식", "쇼핑", "문화"]
    ui_group_label = "👥 누구와? (Group)"
    ui_group_opts = ["혼자", "연인", "친구", "부모님", "어린이"]
    ui_msg_filter = "🎯 원하는 여행 스타일을 콕콕 찍어보세요!"
    ui_msg_result = "🔍 **검색 결과:** 총"
    ui_msg_no_result = "조건에 맞는 장소가 없거나, 시간을 선택하지 않으셨습니다. 😅"
    ui_btn_map = "🗺️ 지도 보기"
    ui_btn_img = "📸 사진 보기"
    ui_tag_info = "📢 **선택된 태그:**"
    ui_btn_reset = "🔄 태그 초기화"

else: # English
    # [Data Columns]
    col_name = 'Name_EN'
    col_desc = 'Description_EN'
    col_area = 'Area_EN'
    col_hub  = 'Hub_EN'
    col_cat  = 'Category_EN'
    col_grp  = 'Group_EN'
    col_map  = 'Google_Map_EN'
    col_img  = 'Google_Image_EN'
    
    # [UI Text]
    ui_title = "🐙 Osaka/Kyoto Travel Guide"
    ui_hub_label = "🏨 Your Hotel (Hub)"
    ui_hub_opts = ["Namba", "Umeda", "Kyoto Station"] # Hub_EN 데이터와 일치해야 함
    ui_time_label = "⏰ Travel Time (Multi-select)"
    ui_time_opts = ["Within 30 min", "30~60 min", "1~2 hours"]
    ui_theme_label = "🏷️ Theme (Category)"
    ui_theme_opts = ["Nature", "City", "History/Culture", "Relax", "Shopping"]
    ui_group_label = "👥 With whom? (Group)"
    ui_group_opts = ["Solo", "Couple", "Friends", "Parents", "Kids"]
    ui_msg_filter = "🎯 Select your travel style!"
    ui_msg_result = "🔍 **Results:** Total"
    ui_msg_no_result = "No places found matching your criteria. 😅"
    ui_btn_map = "🗺️ Google Map"
    ui_btn_img = "📸 Gallery"
    ui_tag_info = "📢 **Selected Tags:**"
    ui_btn_reset = "🔄 Reset Tags"

# ---------------------------------------------------------
# 3. 로직 함수 (시간 계산)
# ---------------------------------------------------------
def calculate_total_time(user_hub, place_hub, deep_time):
    # 허브 간 이동 시간 (한국어/영어 모두 대응하도록 매핑 필요하지만, 
    # 간단하게 영문 Hub 이름도 내부적으로는 한글 로직을 태우거나, 
    # 여기서는 '선택된 옵션의 인덱스'로 판단하는게 안전함. 
    # 하지만 일단 텍스트 매칭으로 구현)
    
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
    
    # 숙소 선택 (언어별 옵션 사용)
    user_hub = st.selectbox(ui_hub_label, ui_hub_opts)
    
    # 시간 선택
    st.subheader(ui_time_label)
    # pills가 지원되면 pills 사용, 아니면 multiselect
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
# 1) 시간 계산 (현재 언어의 Hub 컬럼 사용)
df['Total_Time'] = df.apply(lambda row: calculate_total_time(user_hub, row[col_hub], row['Deep_Time']), axis=1)

# 2) 시간 필터
if not selected_times:
    filtered_df = pd.DataFrame(columns=df.columns)
else:
    conditions = []
    # 선택된 시간 옵션이 무엇인지에 따라 조건 분기
    # (언어가 달라도 리스트 순서는 같으므로 인덱스로 하거나, 문자열 포함으로 처리)
    
    # 30분 이내 (옵션 리스트의 0번째)
    if ui_time_opts[0] in selected_times: 
        conditions.append(df['Total_Time'] <= 30)
    # 30분~1시간 (옵션 리스트의 1번째)
    if ui_time_opts[1] in selected_times: 
        conditions.append((df['Total_Time'] > 30) & (df['Total_Time'] <= 60))
    # 1시간~2시간 (옵션 리스트의 2번째)
    if ui_time_opts[2] in selected_times: 
        conditions.append((df['Total_Time'] > 60) & (df['Total_Time'] <= 120))
    
    if conditions:
        final_condition = conditions[0]
        for c in conditions[1:]: final_condition = final_condition | c
        filtered_df = df[final_condition]
    else:
        filtered_df = df

# 3) 테마 & 그룹 필터 (언어별 컬럼 사용: col_cat, col_grp)
if selected_categories:
    filtered_df = filtered_df[filtered_df[col_cat].apply(lambda x: any(cat in str(x) for cat in selected_categories))]

if selected_groups:
    filtered_df = filtered_df[filtered_df[col_grp].apply(lambda x: any(grp in str(x) for grp in selected_groups))]

# 4) 태그 필터 (태그는 현재 한국어 공통 사용 - 영어 모드에서도 태그 기능 유지)
if st.session_state.selected_tags:
    st.info(f"{ui_tag_info} {', '.join([f'#{t}' for t in st.session_state.selected_tags])}")
    
    pattern = '|'.join(st.session_state.selected_tags)
    # 태그 컬럼은 'Tag' 하나뿐이므로 공통 사용
    filtered_df = filtered_df[filtered_df['Tag'].str.contains(pattern, na=False)]

    if st.button(ui_btn_reset):
        st.session_state.selected_tags = []
        st.rerun()

# 정렬
filtered_df = filtered_df.sort_values('Total_Time')

# ---------------------------------------------------------
# 6. 결과 출력
# ---------------------------------------------------------
st.markdown(f"{ui_msg_result} **{len(filtered_df)}**")

if len(filtered_df) == 0:
    st.warning(ui_msg_no_result)
else:
    # 여기가 263번째 줄 (for 문)
    for index, row in filtered_df.iterrows():
        # [중요] 여기서부터 들여쓰기가 되어야 합니다!
        with st.container():
            # 레이아웃: 왼쪽(설명) 4 : 오른쪽(정보+버튼) 1.5 로 비율 조정
            col1, col2 = st.columns([4, 1.5]) 
            
            with col1:
                # [이름 & 설명]
                st.subheader(f"{row[col_name]}")
                st.write(row[col_desc])
                
                # [위치 정보] (작게 표시)
                st.caption(f"📍 {row[col_area]} (Hub: {row[col_hub]})")

                # [태그 버튼]
                tags = [t.strip() for t in str(row['Tag']).split('#') if t.strip()]
                if tags:
                    cols = st.columns(len(tags) if len(tags) < 10 else 10)
                    for i, tag in enumerate(tags):
                        if i < 10:
                            is_selected = tag in st.session_state.selected_tags
                            label = f"✅ #{tag}" if is_selected else f"#{tag}"
                            cols[i].button(label, key=f"btn_{row['ID']}_{tag}_{index}", on_click=toggle_tag, args=(tag,))

            with col2:
                # [소요시간]
                st.metric(label="Time", value=f"{row['Total_Time']} min")
                
                # [링크 데이터 가져오기]
                map_link = str(row.get(col_map, '')).strip()
                img_link = str(row.get(col_img, '')).strip()
                
                # [버튼 디자인] - st.link_button은 새 탭에서 열려서 아주 편합니다!
                # 1. 지도 버튼
                if map_link.startswith('http'):
                    st.link_button(ui_btn_map, map_link, use_container_width=True)
                else:
                    st.button(ui_btn_map, disabled=True, key=f"map_dis_{index}", use_container_width=True)
                
                # 2. 사진 버튼
                if img_link.startswith('http'):
                    st.link_button(ui_btn_img, img_link, use_container_width=True)
                else:
                    st.button(ui_btn_img, disabled=True, key=f"img_dis_{index}", use_container_width=True)

            st.divider()