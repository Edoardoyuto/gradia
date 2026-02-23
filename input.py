import streamlit as st
import googlemaps
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

#こっちが本ちゃん
def get_route_input(ui_box=st, key_prefix="main"):
    """
    ユーザー入力を受け取るUI部品。
    ui_box: 表示する場所 (st または st.sidebar)
    key_prefix: エラーを防ぐための識別子
    """
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    start_coords, end_coords = None, None

    # --- 1. 出発地点の設定 ---
    ui_box.markdown("### 🟢 出発地点")
    use_current = ui_box.checkbox("現在地を使用する", key=f"{key_prefix}_current")

    if use_current:
        # 現在地取得ボタン（高齢者にもわかりやすいように文字を添える）
        ui_box.info("下のボタンを押して、位置情報を許可してください。")
        location = streamlit_geolocation()
        if location['latitude']:
            start_coords = (location['latitude'], location['longitude'])
            ui_box.success("✅ 現在地をセットしました")
    else:
        start_input = ui_box.text_input("出発地を入力してください", placeholder="例：京都駅", key=f"{key_prefix}_start")
        if start_input:
            res = gmaps.geocode(start_input)
            if res:
                loc = res[0]['geometry']['location']
                start_coords = (loc['lat'], loc['lng'])

    ui_box.markdown("---") # 区切り線で視認性アップ

    # --- 2. 終着地点の設定 ---
    ui_box.markdown("### 🔴 目的地")
    end_input = ui_box.text_input("目的地を入力してください", placeholder="例：二条城", key=f"{key_prefix}_end")
    if end_input:
        res = gmaps.geocode(end_input)
        if res:
            loc = res[0]['geometry']['location']
            end_coords = (loc['lat'], loc['lng'])

    ui_box.markdown("---")

    # --- 3. 距離制限の設定 ---
    ui_box.markdown("### 🚶‍♂️ 無理のない移動距離")
    max_dist = ui_box.slider("何キロまでなら歩けそうですか？", 0.5, 5.0, 2.0, step=0.1, key=f"{key_prefix}_slider")

    # --- 4. 判定とボタン ---
    if start_coords and end_coords:
        dist = geodesic(start_coords, end_coords).km
        if dist > max_dist:
            ui_box.error(f"⚠️ 目的地が遠すぎます（直線距離: {dist:.2f}km）。上限を上げるか、別の場所を選んでください。")
            return None, None
        else:
            ui_box.success(f"直線距離: {dist:.2f}km（設定範囲内です！）")
            
            # 高齢者でも押しやすい大きなボタンにする
            if ui_box.button("✨ この条件でバリアフリールートを探す ✨", use_container_width=True, type="primary", key=f"{key_prefix}_btn"):
                return start_coords, end_coords

    return None, None
