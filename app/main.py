import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import time
import sys
import os
from geopy.distance import geodesic

# --- パスの問題を解決するロジック ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
sys.path.append(project_root)

# 自作エンジンのインポート
from app.input import get_route_input
from src.engine.route_manager import get_walk_network
from src.engine.elevation_manager import ElevationManager
from src.engine.grade_calculator import GradeCalculator

# ページ設定
st.set_page_config(page_title="Universal Topography", layout="wide")

# ==========================================
# キャッシュ管理
# ==========================================

@st.cache_resource
def get_elevation_manager():
    """ElevationManagerのインスタンスを保持し、タイルキャッシュを維持する"""
    return ElevationManager()

@st.cache_data(show_spinner=False)
def preprocess_graph(start_pos, end_pos):
    """道路網取得、標高付与、しんどさ計算の結果をキャッシュする"""
    G = get_walk_network(start_pos, end_pos)
    manager = get_elevation_manager()
    G = manager.enrich_nodes_with_elevation(G)
    calculator = GradeCalculator()
    G = calculator.add_effort_weights(G)
    return G

# --- セッション状態の初期化 ---
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False
if "start_pos" not in st.session_state:
    st.session_state.start_pos = None
if "end_pos" not in st.session_state:
    st.session_state.end_pos = None
if "graph" not in st.session_state:
    st.session_state.graph = None

# ==========================================
# 画面遷移のコントロール
# ==========================================

if not st.session_state.analyzed:
    # --- パターンA：入力画面 ---
    st.title("🗺️ Universal Topography")
    st.markdown("### 誰もが安心して歩ける道をご案内します。")
    st.info("まずは出発地と目的地を教えてください。")
    
    start, end = get_route_input(ui_box=st, key_prefix="main")
    
    if start and end:
        st.session_state.start_pos = start
        st.session_state.end_pos = end
        st.session_state.analyzed = True
        st.rerun() 
else:
    # --- パターンB：解析結果画面 ---
    st.sidebar.title("🔍 条件を変更する")
    new_start, new_end = get_route_input(ui_box=st.sidebar, key_prefix="side")
    
    if new_start and new_end:
        if (new_start != st.session_state.start_pos) or (new_end != st.session_state.end_pos):
            st.session_state.start_pos = new_start
            st.session_state.end_pos = new_end
            st.session_state.graph = None
            st.rerun()
        
    if st.sidebar.button("🏠 最初の画面に戻る", use_container_width=True):
        st.session_state.analyzed = False
        st.session_state.graph = None
        st.rerun()

    st.title("✅ バリアフリー経路の解析結果")
    start_pos = st.session_state.start_pos
    end_pos = st.session_state.end_pos
    
    try:
        if st.session_state.graph is None:
            with st.spinner("道路ネットワークと標高タイルを爆速解析中..."):
                start_time = time.time()
                G = preprocess_graph(start_pos, end_pos)
                st.session_state.graph = G
                elapsed = time.time() - start_time
                st.success(f"🚀 解析完了 (処理時間: {elapsed:.2f}秒)")

        G = st.session_state.graph
        
        # --- ルート計算フェーズ (エッジベースの修正) ---
        # 1. 出発地に一番近い「道(エッジ)」を探す
        nearest_edge_start = ox.distance.nearest_edges(G, start_pos[1], start_pos[0])
        u_start, v_start, key_start = nearest_edge_start
        # 道の両端のうち、より近い方をノードとして採用
        dist_u_start = geodesic((G.nodes[u_start]['y'], G.nodes[u_start]['x']), start_pos).meters
        dist_v_start = geodesic((G.nodes[v_start]['y'], G.nodes[v_start]['x']), start_pos).meters
        origin_node = u_start if dist_u_start < dist_v_start else v_start

        # 2. 目的地に一番近い「道(エッジ)」を探す
        nearest_edge_end = ox.distance.nearest_edges(G, end_pos[1], end_pos[0])
        u_end, v_end, key_end = nearest_edge_end
        dist_u_end = geodesic((G.nodes[u_end]['y'], G.nodes[u_end]['x']), end_pos).meters
        dist_v_end = geodesic((G.nodes[v_end]['y'], G.nodes[v_end]['x']), end_pos).meters
        destination_node = u_end if dist_u_end < dist_v_end else v_end

        # 経路探索
        route = nx.shortest_path(G, origin_node, destination_node, weight='effort')
        shortest_route = nx.shortest_path(G, origin_node, destination_node, weight='length')

        # --- 地図描画 ---
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        # 背景道路
        edges = ox.graph_to_gdfs(G, nodes=False)
        folium.GeoJson(
            edges,
            style_function=lambda x: {'color': '#BBBBBB', 'weight': 1, 'opacity': 0.3}
        ).add_to(m)

        # ルート表示
        s_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_route]
        folium.PolyLine(s_coords, color="#3498DB", weight=4, opacity=0.6, dash_array="5,5").add_to(m)

        r_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
        folium.PolyLine(r_coords, color="#FF4B4B", weight=7, opacity=1.0).add_to(m)

        folium.Marker(start_pos, popup="出発地", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end_pos, popup="目的地", icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width=1000, height=600)

        # レポート表示
        st.markdown("### 📊 ルート比較レポート")
        r_edges = ox.routing.route_to_gdf(G, route)
        s_edges = ox.routing.route_to_gdf(G, shortest_route)
        
        col1, col2 = st.columns(2)
        col1.metric("おすすめ最大斜度", f"{r_edges['slope'].max()*100:.1f} %")
        col2.metric("最短ルート最大斜度", f"{s_edges['slope'].max()*100:.1f} %", 
                    delta=f"{(r_edges['slope'].max() - s_edges['slope'].max())*100:.1f} %", delta_color="inverse")

    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")