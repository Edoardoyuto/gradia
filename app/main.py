import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import sys
import os
import time  # 速度計測用

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
    st.title("🗺️ Universal Topography")
    st.markdown("### 誰もが安心して歩ける道をご案内します。")
    st.info("まずは出発地と目的地を教えてください。")
    
    #
    start, end = get_route_input(ui_box=st, key_prefix="main")
    
    if start and end:
        st.session_state.start_pos = start
        st.session_state.end_pos = end
        st.session_state.analyzed = True
        st.rerun() 
else:
    # --- サイドバー：条件変更 ---
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
                start_time = time.time()  # 計測開始
                
                # 1. 道路ネットワーク取得
                G = get_walk_network(start_pos, end_pos) 
                
                # 2. 標高付与（タイル方式）
                manager = ElevationManager()
                G = manager.enrich_nodes_with_elevation(G) 
                
                # 3. 斜度としんどさ(effort)の計算
                calculator = GradeCalculator()
                G = calculator.add_effort_weights(G) 
                
                elapsed_time = time.time() - start_time  # 計測終了
                st.session_state.graph = G
                st.success(f"🚀 全ての解析が完了しました！ (解析時間: {elapsed_time:.2f}秒)")

        # --- ルート計算フェーズ ---
        G = st.session_state.graph
        #
        origin_node = ox.distance.nearest_nodes(G, start_pos[1], start_pos[0]) 
        destination_node = ox.distance.nearest_nodes(G, end_pos[1], end_pos[0])

        route = None        # バリアフリー用
        shortest_route = None # 最短距離用

        try:
            # バリアフリールート（effort重み）
            route = nx.shortest_path(G, origin_node, destination_node, weight='effort')
            # 最短ルート（length重み）
            shortest_route = nx.shortest_path(G, origin_node, destination_node, weight='length')
        except nx.NetworkXNoPath:
            st.error("経路が見つかりませんでした。")

        # --- 地図の描画 ---
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        #
        nodes, edges = ox.graph_to_gdfs(G) 

        # 背景道路の描画
        def get_color(slope):
            if abs(slope) > 0.1: return "red"
            if slope > 0.05: return "orange"
            if slope < -0.05: return "purple"
            return "#D3D3D3"

        for _, edge in edges.iterrows():
            color = get_color(edge.get('slope', 0))
            folium.PolyLine(
                locations=[(coords[1], coords[0]) for coords in edge.geometry.coords],
                color=color, weight=1, opacity=0.3
            ).add_to(m)

        # 1. 最短経路を「薄い青の点線」で表示
        if shortest_route:
            s_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_route]
            folium.PolyLine(
                locations=s_coords, color="#7FB3D5", weight=4, opacity=0.6,
                dash_array='10, 10', tooltip="最短ルート（坂道考慮なし）"
            ).add_to(m)

        # 2. バリアフリールートを「太い赤線」で表示
        if route:
            r_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
            folium.PolyLine(
                locations=r_coords, color="#FF4B4B", weight=7, opacity=1.0,
                tooltip="おすすめバリアフリールート"
            ).add_to(m)

        folium.Marker(start_pos, popup="START", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end_pos, popup="GOAL", icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width=1000, height=600)

        # --- データ分析レポート ---
        if route and shortest_route:
            st.markdown("### 📊 データ分析：ルート比較レポート")
            #
            r_edges = ox.routing.route_to_gdf(G, route) 
            s_edges = ox.routing.route_to_gdf(G, shortest_route)
            
            max_slope_r = r_edges['slope'].max() * 100
            max_slope_s = s_edges['slope'].max() * 100
            dist_r = r_edges['length'].sum() / 1000
            dist_s = s_edges['length'].sum() / 1000

            col1, col2, col3 = st.columns(3)
            col1.metric("おすすめ距離", f"{dist_r:.2f} km")
            col2.metric("おすすめ最大斜度", f"{max_slope_r:.1f} %")
            col3.metric("最短ルート最大斜度", f"{max_slope_s:.1f} %", 
                        delta=f"{max_slope_r - max_slope_s:.1f} %", delta_color="inverse")

            if max_slope_s > 8:
                st.warning(f"⚠️ 最短ルートには {max_slope_s:.1f}% の急坂が含まれています。車椅子や足腰への負担が大きいため、赤色のルートをお勧めします。")

    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")