

import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx

# main.py の場所を基準に、プロジェクトのルート（gradia/）を検索パスに追加します
current_dir = os.path.dirname(os.path.abspath(__file__)) # app フォルダ
project_root = os.path.join(current_dir, "..")          # gradia フォルダ
sys.path.append(project_root)


# 自作エンジンのインポート
from input import get_route_input
from src.engine.route_manager import get_walk_network
from src.engine.elevation_manager import ElevationManager
from src.engine.grade_calculator import GradeCalculator

# ページ設定
st.set_page_config(page_title="Universal Topography", layout="wide")

# --- セッション状態（記憶）の初期化 ---
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
    # ----------------------------------------
    # パターンA：最初の入力画面
    # ----------------------------------------
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
    # ----------------------------------------
    # パターンB：解析結果画面
    # ----------------------------------------
    st.sidebar.title("🔍 条件を変更する")
    new_start, new_end = get_route_input(ui_box=st.sidebar, key_prefix="side")
    
    if new_start and new_end:
        if (new_start != st.session_state.start_pos) or (new_end != st.session_state.end_pos):
            st.session_state.start_pos = new_start
            st.session_state.end_pos = new_end
            st.session_state.graph = None # 位置が変わったら再解析
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
            with st.spinner("道路ネットワークと標高、移動負荷を解析中..."):
                # 1. 道路ネットワーク取得
                G = get_walk_network(start_pos, end_pos)
                
                # 2. 標高付与
                manager = ElevationManager()
                G = manager.enrich_nodes_with_elevation(G)
                
                # 3. 斜度としんどさ(effort)の計算
                calculator = GradeCalculator()
                G = calculator.add_effort_weights(G)
                
                st.session_state.graph = G
                st.success("全ての解析が完了しました！")

        # --- 最短（最楽）経路の計算 ---
        G = st.session_state.graph
        
        # 出発地と目的地に最も近いノードを探す
        origin_node = ox.distance.nearest_nodes(G, start_pos[1], start_pos[0])
        destination_node = ox.distance.nearest_nodes(G, end_pos[1], end_pos[0])
        
        route = None
        try:
            # 距離ではなく計算した 'effort' を重みにしてダイクストラ実行
            route = nx.shortest_path(G, origin_node, destination_node, weight='effort')
        except nx.NetworkXNoPath:
            st.error("適切なルートが見つかりませんでした。範囲を広げるか別の地点をお試しください。")

        # --- 地図の描画 ---
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        nodes, edges = ox.graph_to_gdfs(G)

        # 全ての道路を背景として描画
        def get_color(slope):
            if abs(slope) > 0.1: return "red"    # 10%超
            if slope > 0.05: return "orange"     # 5%超(上り)
            if slope < -0.05: return "purple"    # 5%超(下り)
            return "#D3D3D3"                     # 平坦な背景道

        for _, edge in edges.iterrows():
            color = get_color(edge.get('slope', 0))
            folium.PolyLine(
                locations=[(coords[1], coords[0]) for coords in edge.geometry.coords],
                color=color,
                weight=1,
                opacity=0.3
            ).add_to(m)

        # 最良ルート（一本道）を太い線で重ねる
        if route:
            route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
            folium.PolyLine(
                locations=route_coords,
                color="#FF4B4B",
                weight=6,
                opacity=1.0,
                tooltip="おすすめバリアフリールート"
            ).add_to(m)
            st.success("✨ 最も負担の少ないルートを表示しています。")

        # 出発地と目的地のマーカー
        folium.Marker(start_pos, popup="START", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end_pos, popup="GOAL", icon=folium.Icon(color="red")).add_to(m)
        
        # 地図を表示
        st_folium(m, width=1000, height=600)

        # 統計情報の表示
        col1, col2, col3 = st.columns(3)
        col1.metric("解析した交差点数", len(G.nodes))
        col2.metric("解析した道路数", len(G.edges))
        if route:
            # 簡易的なルート合計距離の計算
            # ox.routing.route_to_gdf を使うのが現在の推奨です
            route_edges = ox.routing.route_to_gdf(G, route)
            route_length = route_edges['length'].sum()
            col3.metric("ルート総距離", f"{route_length/1000:.2f} km")

    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")