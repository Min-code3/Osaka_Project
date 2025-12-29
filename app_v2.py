import streamlit as st
import pandas as pd
import os
import base64
import csv  # [LOG] 로그 저장을 위한 라이브러리 추가
from datetime import datetime # [LOG] 시간 기록을 위한 라이브러리 추가

# ---------------------------------------------------------
# [LOG] 0. 로그 수집 함수 (여기에 데이터가 쌓입니다!)
# ---------------------------------------------------------
def log_user_action(action_type, detail):
    """
    사용자의 행동을 user_logs.csv 파일에 기록합니다.
    형식: [시간, 행동유형, 세부내용]
    """
    file_name = "user_logs.csv"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 데이터 리스트 생성
    log_data = [current_time, action_type, detail]
    
    # 파일이 없으면 헤더 생성, 있으면 내용 추가 (append 모드)
    file_exists = os.path.isfile(file_name)
    
    try:
        with open(file_name, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Time", "Action", "Detail"]) # 헤더
            writer.writerow(log_data)
        # 개발자 확인용 (터미널 출력)
        print(f"📝 [LOG] {current_time} | {action_type} | {detail}")
    except Exception as e:
        print(f"❌ 로그 저장 실패: {e}")

# ---------------------------------------------------------
# [기존 기능] 클릭 가능한 로컬 이미지 HTML 생성
# ---------------------------------------------------------
def get_clickable_image_html(img_path, target_url=None, height="220px"):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        img_style = f'''
            width: 100%; 
            height: {height}; 
            object-fit: cover; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        '''
        
        img_tag = f'<img src="data:image/jpeg;base64,{encoded}" style="{img_style}" onmouseover="this.style.transform=\'scale(1.02)\'" onmouseout="this.style.transform=\'scale(1.0)\'">'
        
        if target_url and str(target_url).startswith('http'):
            return f'<a href="{target_url}" target="_blank" style="text-decoration: none;">{img_tag}</a>'
        else:
            return img_tag
    else:
        return None

# ---------------------------------------------------------
# 0. 세션 상태 초기화 및 태그 함수 수정
# ---------------------------------------------------------
if 'selected_tags' not in st.session_state:
    st.session_state.selected_tags = []

def toggle_tag(tag):
    if tag in st.session_state.selected_tags:
        st.session_state.selected_tags.remove(tag)
        # [LOG] 태그 해제 로그
        log_user_action("Tag_Remove", tag)
    else:
        st.session_state.selected_tags.append(tag)
        # [LOG] 태그 선택 로그
        log_user_action("Tag_Click", tag)

# ---------------------------------------------------------
# 1. 데이터 로드
# ---------------------------------------------------------
st.set_page_config(page_title="Osaka Travel Guide Project 2", layout="wide")

# @st.cache_data 
def load_data():
    try:
        df = pd.read_excel("data.xlsx")
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None
    
    if 'Name_KR' in df.columns:
        df = df.dropna(subset=['Name_KR'])
    
    if 'Deep_Time' in df.columns:
        df['Deep_Time'] = df['Deep_Time'].astype(str).str.replace('분', '').str.strip()
        df['Deep_Time'] = pd.to_numeric(df['Deep_Time'], errors='coerce').fillna(0).astype(int)
    
    df = df.fillna("")
    return df

df = load_data()

if df is None:
    st.error("🚨 'data.xlsx' 파일을 찾을 수 없거나 읽을 수 없습니다.")
    st.stop()

# ---------------------------------------------------------
# 2. 언어 설정 및 UI 텍스트
# ---------------------------------------------------------
with st.sidebar:
    language = st.radio("🌐 Language / 언어", ["🇰🇷 한국어", "🇺🇸 English"])
    
    # [LOG] 언어 변경 로그 (값이 바뀔 때만 기록하려면 session_state 활용 필요하지만, 여기선 단순화)
    # log_user_action("Language_Set", language) 
    st.divider()

if language == "🇰🇷 한국어":
    col_name, col_desc, col_area, col_hub, col_cat, col_grp, col_tag, col_map, col_img = 'Name_KR', 'Description_KR', 'Area_KR', 'Hub_KR', 'Category_KR', 'Group_KR', 'Tag_KR', 'Google_Map_KR', 'Google_Image_KR'
    ui_title = "🐙 오사카/교토 여행 큐레이션 (Ver 2.0)"
    ui_hub_label, ui_hub_opts = "🏨 숙소(출발지)", ["난바", "우메다", "교토역"]
    ui_time_label, ui_time_opts = "⏰ 소요 시간 (중복 선택)", ["30분 이내", "30분~1시간", "1시간~2시간"]
    ui_theme_label, ui_theme_opts = "🏷️ 테마 (Category)", ["자연", "도시", "역사/전통", "휴식", "쇼핑", "문화"]
    ui_group_label, ui_group_opts = "👥 누구와? (Group)", ["혼자", "연인", "친구", "부모님", "어린이"]
    ui_msg_filter, ui_msg_result, ui_msg_no_result = "🎯 원하는 여행 스타일을 콕콕 찍어보세요!", "🔍 **검색 결과:** 총", "조건에 맞는 장소가 없거나, 시간을 선택하지 않으셨습니다. 😅"
    ui_expander_label, ui_btn_map, ui_tag_info, ui_btn_reset, ui_img_missing = "📝 상세정보 보기 (Click)", "🗺️ 지도 보기", "📢 **선택된 태그:**", "🔄 태그 초기화", "이미지 준비중"
else:
    col_name, col_desc, col_area, col_hub, col_cat, col_grp, col_tag, col_map, col_img = 'Name_EN', 'Description_EN', 'Area_EN', 'Hub_EN', 'Category_EN', 'Group_EN', 'Tag_EN', 'Google_Map_EN', 'Google_Image_EN'
    ui_title = "🐙 Osaka/Kyoto Travel Guide (Ver 2.0)"
    ui_hub_label, ui_hub_opts = "🏨 Your Hotel (Hub)", ["Namba", "Umeda", "Kyoto Station"]
    ui_time_label, ui_time_opts = "⏰ Travel Time (Multi-select)", ["Within 30 min", "30~60 min", "1~2 hours"]
    ui_theme_label, ui_theme_opts = "🏷️ Theme (Category)", ["Nature", "City", "History/Culture", "Relax", "Shopping"]
    ui_group_label, ui_group_opts = "👥 With whom? (Group)", ["Solo", "Couple", "Friends", "Parents", "Kids"]
    ui_msg_filter, ui_msg_result, ui_msg_no_result = "🎯 Select your travel style!", "🔍 **Results:** Total", "No places found matching your criteria. 😅"
    ui_expander_label, ui_btn_map, ui_tag_info, ui_btn_reset, ui_img_missing = "📝 View Details (Click)", "🗺️ Google Map", "📢 **Selected Tags:**", "🔄 Reset Tags", "Image coming soon"

# ---------------------------------------------------------
# 3. 로직 함수 (시간 계산)
# ---------------------------------------------------------
def calculate_total_time(user_hub, place_hub, deep_time):
    hub_map = {"Namba": "난바", "Umeda": "우메다", "Kyoto Station": "교토역", "난바": "난바", "우메다": "우메다", "교토역": "교토역"}
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

with st.sidebar:
    st.header("⚙️ Settings")
    user_hub = st.selectbox(ui_hub_label, ui_hub_opts)
    st.subheader(ui_time_label)
    selected_times = st.pills("Time", ui_time_opts, selection_mode="multi", default=[ui_time_opts[0], ui_time_opts[1]])
    
    # [LOG] 필터가 바뀔 때마다 로그를 남기기 위해 session_state 체크 (간소화 버전)
    # 실제로는 값이 변할 때만 기록해야 중복을 막을 수 있습니다.
    
    st.divider()
    view_mode = st.radio("👀 View Mode", ["List (1열 - Mobile)", "Gallery (3열 - PC)"], index=1)
    st.caption("Designed by JSM | Ver 2.0 (Global)")

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
df['Total_Time'] = df.apply(lambda row: calculate_total_time(user_hub, row[col_hub], row['Deep_Time']), axis=1)

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

if selected_categories:
    filtered_df = filtered_df[filtered_df[col_cat].apply(lambda x: any(cat in str(x) for cat in selected_categories))]
if selected_groups:
    filtered_df = filtered_df[filtered_df[col_grp].apply(lambda x: any(grp in str(x) for grp in selected_groups))]

if st.session_state.selected_tags:
    st.info(f"{ui_tag_info} {', '.join([f'#{t}' for t in st.session_state.selected_tags])}")
    pattern = '|'.join(st.session_state.selected_tags)
    filtered_df = filtered_df[filtered_df[col_tag].str.contains(pattern, na=False)]

    if st.button(ui_btn_reset):
        st.session_state.selected_tags = []
        log_user_action("Tag_Reset", "All Cleared") # [LOG] 초기화 로그
        st.rerun()

filtered_df = filtered_df.sort_values('Total_Time')

# ---------------------------------------------------------
# 6. 결과 출력
# ---------------------------------------------------------
st.markdown(f"{ui_msg_result} **{len(filtered_df)}**")

# [LOG] 검색 결과 수 기록 (사용자가 어떤 조건으로 검색했는지 간접 파악)
# 너무 자주 기록되면 파일이 커질 수 있으므로 주의 필요
# log_user_action("Search_Result", f"Count: {len(filtered_df)}")

if len(filtered_df) == 0:
    st.warning(ui_msg_no_result)
else:
    if "Gallery" in view_mode:
        num_columns = 3
    else:
        num_columns = 1

    rows = [filtered_df.iloc[i:i + num_columns] for i in range(0, len(filtered_df), num_columns)]

    for row_data in rows:
        cols = st.columns(num_columns)
        
        for col, (index, row) in zip(cols, row_data.iterrows()):
            with col:
                # --- [A] 이미지 ---
                img_path = os.path.join("images", f"{row['Name_EN']}.jpg")
                target_link = str(row.get(col_img, '')).strip()
                img_height = "200px" if num_columns > 1 else "250px"
                
                html_code = get_clickable_image_html(img_path, target_link, height=img_height)
                
                if html_code:
                    st.markdown(html_code, unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ {ui_img_missing}")
                    st.markdown(f'<div style="height:{img_height}; bg-color:#eee;"></div>', unsafe_allow_html=True)

                # --- [B] 정보 ---
                info_text = f"⏱️ {row['Total_Time']} min | 📍 {row[col_area]}"
                st.markdown(f"""
                    <div style="margin-top: 5px; margin-bottom: 10px; line-height: 1.2;">
                        <span style="font-size: 1.1em; font-weight: bold;">{row[col_name]}</span><br>
                        <span style="font-size: 0.85em; color: gray;">{info_text}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # --- [C] 상세정보 (태그 클릭 추적) ---
                with st.expander(ui_expander_label):
                    st.write(row[col_desc])
                    st.divider()
                    
                    tags = [t.strip() for t in str(row[col_tag]).split('#') if t.strip()]
                    
                    if tags:
                        st.caption("🏷️ Tags (Click to filter)")
                        tag_cols = st.columns(len(tags) if len(tags) < 5 else 5)
                        for i, tag in enumerate(tags):
                            current_col = tag_cols[i % 5] 
                            is_selected = tag in st.session_state.selected_tags
                            label = f"✅{tag}" if is_selected else f"#{tag}"
                            
                            # 기존 기능 + 로그 기능 통합
                            current_col.button(
                                label, 
                                key=f"btn_{index}_{tag}", 
                                on_click=toggle_tag, 
                                args=(tag,),
                                use_container_width=True 
                            )
                        st.divider()

                    map_link = str(row.get(col_map, '')).strip()
                    if map_link.startswith('http'):
                        # [참고] st.link_button은 클릭 시 브라우저가 이동하므로 
                        # Python 내부에서 '클릭 로그'를 남기기 어렵습니다. 
                        # (로그를 남기고 이동하려면 JavaScript가 필요함)
                        st.link_button(ui_btn_map, map_link, use_container_width=True)
                    else:
                        st.button(ui_btn_map, disabled=True, key=f"map_dis_{index}", use_container_width=True)
                
                st.write("---")

# ---------------------------------------------------------
# [관리자 기능] URL로 숨겨진 관리자 모드 (Backdoor)
# 이 코드를 app.py의 맨 마지막에 붙여넣으세요.
# ---------------------------------------------------------

# 1. 주소창에 '?admin=true'가 있는지 몰래 확인
# (예: https://your-app-url.streamlit.app/?admin=true)
query_params = st.query_params

# 👇 기존의 if문 대신 이걸 써보세요 (무조건 보여주는 코드)
if True: 
    st.divider()
    st.error("🚨 관리자 모드 강제 실행 중 (들여쓰기 확인용)")
    
    # ... (나머지 코드는 그대로 둠)
    
    # 2. 관리자 비밀번호 설정 (원하는 걸로 바꾸세요!)
    ADMIN_PASSWORD = "1234" 
    
    # 3. 비밀번호 입력창
    input_pw = st.text_input("관리자 암호를 입력하세요 (Password)", type="password")
    
    if input_pw == ADMIN_PASSWORD:
        st.success("로그인 성공! 데이터를 불러옵니다.")
        
        # 파일이 실제로 있는지 확인
        if os.path.exists("user_logs.csv"):
            # 로그 파일 읽기
            log_df = pd.read_csv("user_logs.csv")
            
            # 최신순(시간 역순)으로 정렬해서 보여주기
            st.dataframe(log_df.sort_values("Time", ascending=False), use_container_width=True)
            
            # 다운로드 버튼 생성
            csv_data = log_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 로그 데이터 다운로드 (Download CSV)",
                data=csv_data,
                file_name="user_logs.csv",
                mime="text/csv",
            )
        else:
            st.warning("아직 수집된 로그 데이터가 없습니다. (No logs yet)")
            
    elif input_pw:
        st.error("비밀번호가 틀렸습니다! (Wrong Password)")

# 디버깅용: 현재 앱이 인식하는 주소창 파라미터를 화면에 출력
st.write("현재 인식된 파라미터:", st.query_params)
