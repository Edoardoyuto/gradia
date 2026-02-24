import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import time
import sys
import os

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
# キャッシュ管理：ここが高速化の核心
# ==========================================

@st.cache_resource
def get_elevation_manager():
    """
    ElevationManagerのインスタンスを保持。
    これにより内部の tile_cache (PNGデータ) がセッションを越えて維持される。
    """
    return ElevationManager()

@st.cache_data(show_spinner=False)
def preprocess_graph(start_pos, end_pos):
    """
    道路網取得、標高付与、しんどさ計算までを一括で行い、結果をキャッシュする。
    """
    # 1. 道路ネットワーク取得
    G = get_walk_network(start_pos, end_pos)

    # 2. 標高付与（タイルキャッシュを保持するマネージャーを使用）
    manager = get_elevation_manager()
    G = manager.enrich_nodes_with_elevation(G)

    # 3. 斜度としんどさ(effort)の計算
    calculator = GradeCalculator()
    G = calculator.add_effort_weights(G)

    return G

# ==========================================
# メイン画面
# ==========================================

st.title("🗺️ Universal Topography")

# 入力UIの呼び出し
start, end = get_route_input(ui_box=st)

if start and end:
    try:
        # --- 高速解析フェーズ ---
        with st.spinner("地形と道路網を爆速解析中..."):
            start_time = time.time()
            # キャッシュが効くため、同じ地点なら一瞬で終わる
            G = preprocess_graph(start, end)
            elapsed = time.time() - start_time
            st.success(f"🚀 解析完了（処理時間: {elapsed:.2f}秒）")

        # --- ルート探索 ---
        # 出発地と目的地に最も近いノードを特定
        origin_node = ox.distance.nearest_nodes(G, start[1], start[0])
        destination_node = ox.distance.nearest_nodes(G, end[1], end[0])

        # ダイクストラ法による経路探索
        # おすすめルート（effortを重みに使用）
        route = nx.shortest_path(G, origin_node, destination_node, weight='effort')
        # 最短ルート（距離を重みに使用）
        shortest_route = nx.shortest_path(G, origin_node, destination_node, weight='length')

        # --- 地図の描画 ---
        center_lat = (start[0] + end[0]) / 2
        center_lon = (start[1] + end[1]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)

        # 道路ネットワークの背景描画（ノードは除外して軽くする）
        edges = ox.graph_to_gdfs(G, nodes=False)
        folium.GeoJson(
            edges,
            style_function=lambda x: {
                'color': '#BBBBBB',
                'weight': 1,
                'opacity': 0.3
            }
        ).add_to(m)

        # 1. 最短ルート（点線）
        s_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_route]
        folium.PolyLine(
            s_coords, color="#3498DB", weight=4, opacity=0.6, 
            dash_array="5,5", tooltip="最短ルート（坂道考慮なし）"
        ).add_to(m)

        # 2. バリアフリールート（赤太線）
        r_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
        folium.PolyLine(
            r_coords, color="#FF4B4B", weight=7, opacity=1.0,
            tooltip="おすすめバリアフリールート"
        ).add_to(m)

        # マーカー設定
        folium.Marker(start, popup="出発地", icon=folium.Icon(color="green", icon="info-sign")).add_to(m)
        folium.Marker(end, popup="目的地", icon=folium.Icon(color="red", icon="flag")).add_to(m)

        # 地図表示
        st_folium(m, width=1000, height=600)

        # --- 比較レポートの表示 ---
        st.markdown("### 📊 ルート比較")
        r_edges = ox.routing.route_to_gdf(G, route)
        s_edges = ox.routing.route_to_gdf(G, shortest_route)
        
        col1, col2 = st.columns(2)
        col1.metric("おすすめの最大斜度", f"{r_edges['slope'].max()*100:.1f} %")
        col2.metric("最短ルートの最大斜度", f"{s_edges['slope'].max()*100:.1f} %", 
                    delta=f"{(r_edges['slope'].max() - s_edges['slope'].max())*100:.1f} %", delta_color="inverse")

    except Exception as e:
        st.error(f"解析中にエラーが発生しました。範囲を広げるか、別の地点をお試しください。")
        st.info(f"詳細エラー: {e}")