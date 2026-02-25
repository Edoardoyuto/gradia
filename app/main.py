import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import sys
import os
from geopy.distance import geodesic




ox.settings.overpass_endpoint = "https://overpass.kumi.systems/api/interpreter"

# -----------------------
# パス設定
# -----------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
sys.path.append(project_root)

from app.input import get_route_input
from src.engine.route_manager import get_walk_network
from src.engine.elevation_manager import ElevationManager
from src.engine.grade_calculator import GradeCalculator

# -----------------------
# 1. ページ設定 (必ず最初に実行)
# -----------------------
st.set_page_config(
    page_title="Gradia",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# 2. Session State 初期化 (★CSSの前に記述することでエラーを回避)
# -----------------------
for key in ["analyzed", "start_pos", "end_pos", "graph", "route", "shortest_route"]:
    if key not in st.session_state:
        # analyzedはTrue/False、その他はNoneで初期化
        st.session_state[key] = False if key == "analyzed" else None

# -----------------------
# 3. CSS定義 (動的レイアウト)
# -----------------------
# 初期化が済んでいるので、ここでst.session_state.analyzedを参照してもエラーになりません
max_width_value = "500px" if not st.session_state.analyzed else "100%"

st.markdown(f"""
<style>
/* 1. メインコンテナの動的制御 */
.block-container {{
    max-width: {max_width_value} !important;
    padding-top: 2rem !important;
    padding-bottom: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
}}

/* 2. サイドバー固定幅 */
section[data-testid="stSidebar"] {{
    min-width: 415px !important;
    max-width: 415px !important;
}}

/* 3. 要素間の隙間を極限までカット */
[data-testid="stVerticalBlock"] > div {{
    padding: 0px !important;
    gap: 0.5rem !important;
}}

/* 4. 指標(Metric)のスタイル */
[data-testid="stMetricLabel"] > div {{
    white-space: normal !important;
    line-height: 1.2 !important;
    min-height: 2.4em;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.5rem !important;
}}
/* 3. Markdown要素内の段落(p)が持つデフォルトの余白を消す */
.stMarkdown p {{
    margin-bottom: 0px !important;
}}
/* 5. フォーム・テキスト周りの装飾 */
h2 {{
    margin-top: 0.5rem !important;
    line-height: 1.1 !important;
    color: #333 !important;
    text-align: center;
}}

.stCaption {{
    margin-top: -0.5rem !important;
    text-align: center;
}}
/* 2. 水平線 (hr) の上下余白を最小化 */
hr {{
    margin-top: 0rem !important;    /* 線の上側の隙間をゼロに */
    margin-bottom: 0.5rem !important; /* 線の直後の入力欄との距離を微調整 */
}}
/* 6. 背景設定 */
.stApp {{
    background-image: linear-gradient(
        to bottom, 
        rgba(255, 255, 255, 1) 0%, 
        rgba(255, 255, 255, 0.9) 70%, 
        rgba(255, 255, 255, 0) 100%
    ), 
    url("https://www.justonecookbook.com/wp-content/uploads/2016/06/tokyo-tower-map.jpg");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

/* 7. 地図(iframe)の設定 */
iframe {{
    border: none !important;
}}

/* 8. チェックボックスの配置調整 */
div[data-testid="stCheckbox"] {{
    display: flex;
    align-items: center;
    height: 100%;
    margin-top: 5px;
}}

</style>
""", unsafe_allow_html=True)

# -----------------------
# キャッシュ
# -----------------------
@st.cache_resource
def get_elevation_manager():
    return ElevationManager()

@st.cache_data(show_spinner=False)
def preprocess_graph(start_pos, end_pos):
    G = get_walk_network(start_pos, end_pos)
    manager = get_elevation_manager()
    G = manager.enrich_nodes_with_elevation(G)
    calculator = GradeCalculator()
    G = calculator.add_effort_weights(G)
    return G

# -----------------------
# 入力画面 (未解析時)
# -----------------------
if not st.session_state.analyzed:
    # 左右に空の列を作って中央に配置
    _, col_mid, _ = st.columns([0.1, 0.8, 0.1])

    with col_mid:
        st.markdown("## Gradia")
        st.caption("Route Optimization with Elevation Intelligence")
        st.markdown("---")

        start, end = get_route_input(ui_box=st, key_prefix="main")

        if start and end:
            st.session_state.start_pos = start
            st.session_state.end_pos = end
            st.session_state.analyzed = True
            st.rerun()

# -----------------------
# 解析画面
# -----------------------
else:
    # --- サイドバー ---
    with st.sidebar:
        st.markdown("### Gradia")
        st.markdown("---")

        new_start, new_end = get_route_input(ui_box=st, key_prefix="side")

        if new_start and new_end:
            if (new_start != st.session_state.start_pos) or (new_end != st.session_state.end_pos):
                st.session_state.start_pos = new_start
                st.session_state.end_pos = new_end
                st.session_state.graph = None # ここでグラフを消している
                st.session_state.route = None # 【追加】ルートも一緒に消すべき
                st.rerun()

        if st.session_state.route and st.session_state.shortest_route:
            G = st.session_state.graph
            r_edges = ox.routing.route_to_gdf(G, st.session_state.route)
            s_edges = ox.routing.route_to_gdf(G, st.session_state.shortest_route)

            max_slope_r = r_edges['slope'].max() * 100
            max_slope_s = s_edges['slope'].max() * 100
            diff = max_slope_r - max_slope_s

            col1, col2 = st.columns(2)
            col1.metric("最短経路の最大傾斜", f"{max_slope_s:.1f}%")
            
            delta_value = None if abs(diff) < 1e-6 else f"{diff:.1f}%"
            col2.metric(
                "おすすめ経路の最大傾斜", 
                f"{max_slope_r:.1f}%", 
                delta=delta_value, 
                delta_color="inverse"
            )

    # --- メイン（地図表示） ---
    start_pos = st.session_state.start_pos
    end_pos = st.session_state.end_pos

    try:
        if st.session_state.graph is None:
            G = preprocess_graph(start_pos, end_pos)
            st.session_state.graph = G
        else:
            G = st.session_state.graph

        # 最近傍ノード取得
        u_start, v_start, _ = ox.distance.nearest_edges(G, start_pos[1], start_pos[0])
        dist_u = geodesic((G.nodes[u_start]['y'], G.nodes[u_start]['x']), start_pos).meters
        dist_v = geodesic((G.nodes[v_start]['y'], G.nodes[v_start]['x']), start_pos).meters
        origin_node = u_start if dist_u < dist_v else v_start

        u_end, v_end, _ = ox.distance.nearest_edges(G, end_pos[1], end_pos[0])
        dist_u = geodesic((G.nodes[u_end]['y'], G.nodes[u_end]['x']), end_pos).meters
        dist_v = geodesic((G.nodes[v_end]['y'], G.nodes[v_end]['x']), end_pos).meters
        destination_node = u_end if dist_u < dist_v else v_end

        route = nx.shortest_path(G, origin_node, destination_node, weight="effort")
        shortest_route = nx.shortest_path(G, origin_node, destination_node, weight="length")

        st.session_state.route = route
        st.session_state.shortest_route = shortest_route

        # Folium 地図作成
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="cartodbpositron")

        # 経路の描画
        edges = ox.graph_to_gdfs(G, nodes=False)
        folium.GeoJson(edges, style_function=lambda x: {"color": "#DDDDDD", "weight": 1, "opacity": 0.5}).add_to(m)

        s_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in shortest_route]
        folium.PolyLine(s_coords, color="#95a5a6", weight=3, opacity=0.5, dash_array="10,10").add_to(m)

        r_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
        folium.PolyLine(r_coords, color="#2ecc71", weight=6, opacity=0.8).add_to(m)

        folium.Marker(start_pos, icon=folium.Icon(color="gray", icon="play")).add_to(m)
        folium.Marker(end_pos, icon=folium.Icon(color="black", icon="flag")).add_to(m)

        # 地図をコンテナ幅いっぱいに表示
        st_folium(m, width=None, height=800, use_container_width=True)

    except Exception as e:
        st.error(f"Analysis Error: {e}")