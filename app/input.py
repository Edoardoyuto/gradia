import streamlit as st
import googlemaps
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

def get_route_input(ui_box=st, key_prefix="main"):
    """
    ユーザー入力を受け取るUI部品。
    """
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    start_coords, end_coords = None, None

    # --- 1. 出発地点 (スタイリッシュに横並び) ---
    col1, col2 = ui_box.columns([3, 1]) # 割合を微調整
    with col1:
        # stではなくui_box(またはそのカラム)内で入力
        start_input = col1.text_input(
            "Start", placeholder="出発地（例：二条駅）", 
            key=f"{key_prefix}_start", label_visibility="collapsed"
        )
    with col2:
        use_current = col2.checkbox("現在地", key=f"{key_prefix}_current")

    if use_current:
        location = streamlit_geolocation()
        if location['latitude']:
            start_coords = (location['latitude'], location['longitude'])
    elif start_input:
        res = gmaps.geocode(start_input)
        if res:
            loc = res[0]['geometry']['location']
            start_coords = (loc['lat'], loc['lng'])

    # --- 2. 目的地 ---
    end_input = ui_box.text_input(
        "End", placeholder="目的地（例：二条城）", 
        key=f"{key_prefix}_end", label_visibility="collapsed"
    )
    if end_input:
        res = gmaps.geocode(end_input)
        if res:
            loc = res[0]['geometry']['location']
            end_coords = (loc['lat'], loc['lng'])

    # --- 3. 距離制限 ---
    ui_box.markdown("###### どれくらい歩けそうですか？")
    
    # 選択肢の定義
    dist_options = {
        0.5: "0.5km", 0.8: "0.8km", 1.0: "1.0km", 1.2: "1.2km", 
        1.5: "1.5km", 2.0: "2.0km", 3.0: "3.0km", 5.0: "5.0km"
    }

    selected_label = ui_box.select_slider(
        "移動の目安", 
        options=list(dist_options.values()), 
        value=dist_options[2.0],
        key=f"{key_prefix}_slider",
        label_visibility="collapsed"
    )

    # 数値への逆引き
    max_dist = [k for k, v in dist_options.items() if v == selected_label][0]
    
    # スタイリッシュな強調表示
    ui_box.caption(f"現在の設定：直線距離 {max_dist}km 以内のルートを探します")

    # --- 4. 実行判定 (常に表示するスタイル) ---
    search_button = ui_box.button("ルートを検索", use_container_width=True, type="primary")

    if search_button:
        if not start_coords or not end_coords:
            ui_box.warning("出発地と目的地を入力してください。")
        else:
            dist = geodesic(start_coords, end_coords).km
            if dist <= max_dist:
                return start_coords, end_coords
            else:
                ui_box.error(f"目的地が遠すぎます ({dist:.1f}km)")

    return None, None