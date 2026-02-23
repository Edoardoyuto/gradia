import streamlit as st
import googlemaps
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

def get_route_input():
    """
    ユーザーから出発地・目的地の入力を受け取り、それぞれの(lat, lng)を返す関数。
    直線距離の制約チェックも行う。
    """
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
    
    start_coords = None
    end_coords = None

    st.sidebar.title("🗺️ 経路設定")

    # --- 1. 出発地点の設定 ---
    st.sidebar.subheader("① 出発地点")
    use_current = st.sidebar.checkbox("現在地を使用する")
    
    if use_current:
        location = streamlit_geolocation()
        if location['latitude']:
            start_coords = (location['latitude'], location['longitude'])
            st.sidebar.success("現在地をセットしました")
    else:
        start_input = st.sidebar.text_input("出発地を入力", placeholder="例：京都駅")
        if start_input:
            res = gmaps.geocode(start_input)
            if res:
                loc = res[0]['geometry']['location']
                start_coords = (loc['lat'], loc['lng'])

    # --- 2. 終着地点の設定 ---
    st.sidebar.subheader("② 目的地")
    end_input = st.sidebar.text_input("目的地を入力", placeholder="例：二条城")
    if end_input:
        res = gmaps.geocode(end_input)
        if res:
            loc = res[0]['geometry']['location']
            end_coords = (loc['lat'], loc['lng'])

    # --- 3. 距離制限の設定 ---
    st.sidebar.subheader("③ 移動制限")
    max_dist = st.sidebar.slider("許容する最大直線距離 (km)", 0.5, 5.0, 2.0, step=0.1)

    # --- 4. バリデーションと結果の返却 ---
    if start_coords and end_coords:
        # 直線距離を計算 (単位: km)
        dist = geodesic(start_coords, end_coords).km
        
        if dist > max_dist:
            st.sidebar.error(f"⚠️ 距離が遠すぎます！\n現在の直線距離: {dist:.2f}km\n設定上限: {max_dist}km")
            return None, None
        else:
            st.sidebar.success(f"直線距離: {dist:.2f}km (許容範囲内)")
            if st.sidebar.button("この条件で経路解析を開始"):
                return start_coords, end_coords

    return None, None

# メイン処理での使い方
# start_pos, end_pos = get_route_input()
# if start_pos and end_pos:
#     # ここから古田さんの解析エンジンへデータを渡す
#     pass