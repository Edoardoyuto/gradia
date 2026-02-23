import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import st_folium
from src.engine.route_manager import get_walk_network

st.set_page_config(page_title="Network Test", layout="wide")
st.title("🌐 道路ネットワーク取得テスト")

start_coords = (35.0111, 135.7482)
end_coords = (35.0116, 135.7618)

st.write(f"📍 出発地座標: {start_coords}")
st.write(f"📍 目的地座標: {end_coords}")

# ===== 追加：記憶領域の準備 =====
if "show_map" not in st.session_state:
    st.session_state.show_map = False

# ボタンが押されたら、記憶を「True」に書き換える
if st.button("地図データを取得して表示する"):
    st.session_state.show_map = True

# ===== 変更：ボタンのON/OFFではなく、記憶がTrueかどうかで判定 =====
if st.session_state.show_map:
    try:
        with st.spinner("OpenStreetMapから道路網をダウンロード中..."):
            G = get_walk_network(start_coords, end_coords)
            st.success("✅ 道路ネットワークの取得に成功しました！")
            
            st.markdown("### 🗺️ 取得したネットワークの可視化")
            
            center_lat = (start_coords[0] + end_coords[0]) / 2
            center_lng = (start_coords[1] + end_coords[1]) / 2
            m = folium.Map(location=[center_lat, center_lng], zoom_start=15) # ズーム少し寄りました
            
            nodes, edges = ox.graph_to_gdfs(G)
            
            col1, col2 = st.columns(2)
            col1.metric("交差点（ノード）の数", len(nodes))
            col2.metric("道（エッジ）の数", len(edges))
            
            folium.GeoJson(
                edges,
                style_function=lambda x: {'color': '#1E90FF', 'weight': 2, 'opacity': 0.5}
            ).add_to(m)
            
            folium.Marker(start_coords, popup="START", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(end_coords, popup="GOAL", icon=folium.Icon(color="red")).add_to(m)
            
            st_folium(m, width=900, height=600)
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")