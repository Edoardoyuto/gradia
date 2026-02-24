import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import sys
import os
from geopy.distance import geodesic

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
# ページ設定
# -----------------------
st.set_page_config(
    page_title="Gradia",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# CSS（スクロール削減版）
# -----------------------
# -----------------------
# CSS（見切れ解消＆極限タイト版）
# -----------------------
st.markdown("""
<style>
/* 1. サイドバーの幅を固定 (例: 350px) */
section[data-testid="stSidebar"] {
    min-width: 400px !important;
    max-width: 400px !important;
}
/* 1. 全体のパディングを最小化 */
.block-container {
    padding-top: 1rem !important; /* 見切れ防止のため少しだけ余裕を持たせる */
    padding-bottom: 0rem !important;
}

/* タイトル(h2)の強制表示設定 */
h2 {
    margin-top: 2rem !important; /* マイナスを廃止して確実に出す */
    margin-bottom: 0rem !important;
    padding-top: 0rem !important;
    line-height: 1.1 !important;
    display: block !important;
    color: #333 !important;
}
div[data-testid="stCheckbox"] {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%; /* 入力欄と高さを合わせる */
    margin-top: 5px; /* 微調整 */
}
/* 全体のパディング微調整 */
.block-container {
    padding-top: 1.5rem !important; /* 1remだとブラウザによって見切れるため */
}
/* 3. キャプションと横線の隙間を詰める */
.stCaption {
    margin-top: -0.2rem !important;
    margin-bottom: 0rem !important;
    line-height: 1.2 !important;
}

hr {
    margin-top: 0.3rem !important;
    margin-bottom: 0.5rem !important;
}

/* 5. サイドバーのStats表示をコンパクトに */
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important; /* 数字を少し小さく */
}
.stMetric {
    padding: 5px 10px !important;
}

/* 6. 背景設定（既存維持） */
.stApp {
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
}
            

            
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
# Session State 初期化
# -----------------------
for key in ["analyzed", "start_pos", "end_pos", "graph", "route", "shortest_route"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "analyzed" else False

# -----------------------
# 入力画面
# -----------------------
if not st.session_state.analyzed:

    _, col_mid, _ = st.columns([1, 2, 1])

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

    # -------------------
    # サイドバー
    # -------------------
    with st.sidebar:

        st.markdown("### Gradia")
        st.markdown("---")

        new_start, new_end = get_route_input(ui_box=st, key_prefix="side")

        if new_start and new_end:
            if (new_start != st.session_state.start_pos) or (new_end != st.session_state.end_pos):
                st.session_state.start_pos = new_start
                st.session_state.end_pos = new_end
                st.session_state.graph = None
                st.rerun()

        if st.session_state.route and st.session_state.shortest_route:

            G = st.session_state.graph
            route = st.session_state.route
            shortest_route = st.session_state.shortest_route

            r_edges = ox.routing.route_to_gdf(G, route)
            s_edges = ox.routing.route_to_gdf(G, shortest_route)

            max_slope_r = r_edges['slope'].max() * 100
            max_slope_s = s_edges['slope'].max() * 100
            diff = max_slope_r - max_slope_s

            col1, col2 = st.columns(2)

            col1.metric(
                "最短経路の最大傾斜",
                f"{max_slope_s:.1f}%"
            )

            # diff が 0 のときは delta を None にする
            delta_value = None if abs(diff) < 1e-6 else f"{diff:.1f}%"

            col2.metric(
                "おすすめ経路の最大傾斜",
                f"{max_slope_r:.1f}%",
                delta=delta_value,
                delta_color="inverse"
            )


    # -------------------
    # メイン（地図のみ）
    # -------------------
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

        # 地図表示
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=15,
            tiles="cartodbpositron"
        )

        edges = ox.graph_to_gdfs(G, nodes=False)
        folium.GeoJson(
            edges,
            style_function=lambda x: {
                "color": "#DDDDDD",
                "weight": 1,
                "opacity": 0.5
            }
        ).add_to(m)

        s_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in shortest_route]
        folium.PolyLine(
            s_coords,
            color="#95a5a6",
            weight=3,
            opacity=0.5,
            dash_array="10,10"
        ).add_to(m)

        r_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
        folium.PolyLine(
            r_coords,
            color="#2ecc71",
            weight=6,
            opacity=0.8
        ).add_to(m)

        folium.Marker(start_pos, icon=folium.Icon(color="gray", icon="play")).add_to(m)
        folium.Marker(end_pos, icon=folium.Icon(color="black", icon="flag")).add_to(m)

        st_folium(m, width="100%", height=560)

    except Exception as e:
        st.error(f"Analysis Error: {e}")