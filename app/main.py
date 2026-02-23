import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox

# 自作エンジンのインポート
from app.input import get_route_input
from src.engine.route_manager import get_walk_network
from src.engine.elevation_manager import ElevationManager

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
    # パターンA：最初の画面（メイン画面に入力欄を表示）
    # ----------------------------------------
    st.title("🗺️ Universal Topography")
    st.markdown("### 誰もが安心して歩ける道をご案内します。")
    st.info("まずは出発地と目的地を教えてください。")
    
    # 画面の中央に入力フォームを表示
    start, end = get_route_input(ui_box=st, key_prefix="main")
    
    if start and end:
        # 入力が完了してボタンが押されたら記憶
        st.session_state.start_pos = start
        st.session_state.end_pos = end
        st.session_state.analyzed = True
        st.rerun() 

else:
    # ----------------------------------------
    # パターンB：検索後の画面（結果表示）
    # ----------------------------------------
    st.sidebar.title("🔍 条件を変更する")
    # サイドバーで再検索を可能にする
    new_start, new_end = get_route_input(ui_box=st.sidebar, key_prefix="side")
    
    if new_start and new_end:
        st.session_state.start_pos = new_start
        st.session_state.end_pos = new_end
        st.session_state.graph = None  # 新しい地点なのでグラフをリセット
        st.rerun()
        
    if st.sidebar.button("🏠 最初の画面に戻る", use_container_width=True):
        st.session_state.analyzed = False
        st.session_state.start_pos = None
        st.session_state.end_pos = None
        st.session_state.graph = None
        st.rerun()

    # --- メイン解析処理 ---
    st.title("✅ バリアフリー経路の解析結果")
    start_pos = st.session_state.start_pos
    end_pos = st.session_state.end_pos
    
    try:
        # まだグラフ（道路・標高データ）が生成されていない場合のみ解析を実行
        if st.session_state.graph is None:
            with st.spinner("道路ネットワークと標高データを解析中..."):
                # 1. 道路ネットワーク取得
                G = get_walk_network(start_pos, end_pos)
                
                # 2. 標高付与（自動的に保存される）
                manager = ElevationManager()
                G = manager.enrich_nodes_with_elevation(G)
                
                st.session_state.graph = G
                st.success("データの取得と標高の付与が完了しました。")

        # --- 地図の描画 ---
        G = st.session_state.graph
        center_lat = (start_pos[0] + end_pos[0]) / 2
        center_lon = (start_pos[1] + end_pos[1]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        # 道路（エッジ）を地図に追加
        nodes, edges = ox.graph_to_gdfs(G)
        folium.GeoJson(
            edges,
            style_function=lambda x: {'color': '#1E90FF', 'weight': 2, 'opacity': 0.6},
            tooltip="道路データ"
        ).add_to(m)

        # 出発地と目的地のマーカー
        folium.Marker(start_pos, popup="START", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end_pos, popup="GOAL", icon=folium.Icon(color="red")).add_to(m)

        # Streamlit上で地図を表示
        st_folium(m, width=1000, height=600)
        
        # 統計情報の表示
        col1, col2 = st.columns(2)
        col1.metric("解析した交差点数", len(G.nodes))
        col2.metric("解析した道路数", len(G.edges))

    except Exception as e:
        st.error(f"解析中にエラーが発生しました: {e}")
        st.info("APIキーやネットワーク接続、または座標の範囲を確認してください。")