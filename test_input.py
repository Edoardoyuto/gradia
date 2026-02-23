import streamlit as st
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium
from inputdemo import get_route_input

st.set_page_config(page_title="Universal Topography", layout="wide")

# --- セッション状態（記憶）の初期化 ---
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False  # まだ検索していない状態
if "start_pos" not in st.session_state:
    st.session_state.start_pos = None
if "end_pos" not in st.session_state:
    st.session_state.end_pos = None

# ==========================================
# 画面遷移のコントロール
# ==========================================

if not st.session_state.analyzed:
    # ----------------------------------------
    # パターンA：最初の画面（メイン画面に入力欄をドカンと出す）
    # ----------------------------------------
    st.title("🗺️ Universal Topography")
    st.markdown("### 誰もが安心して歩ける道をご案内します。")
    st.info("まずは出発地と目的地を教えてください。")
    
    # 画面の中央（st）に入力フォームを表示
    start, end = get_route_input(ui_box=st, key_prefix="main")
    
    if start and end:
        # 入力が完了してボタンが押されたら、記憶して画面をリロード
        st.session_state.start_pos = start
        st.session_state.end_pos = end
        st.session_state.analyzed = True
        st.rerun() # 画面を再読み込みしてパターンBへ移行

else:
    # ----------------------------------------
    # パターンB：検索後の画面（サイドバーで再検索、メインに結果）
    # ----------------------------------------
    st.sidebar.title("🔍 条件を変更する")
    # サイドバー（st.sidebar）に入力フォームを表示
    new_start, new_end = get_route_input(ui_box=st.sidebar, key_prefix="side")
    
    if new_start and new_end:
        # 再検索されたら値を上書きしてリロード
        st.session_state.start_pos = new_start
        st.session_state.end_pos = new_end
        st.rerun()
        
    if st.sidebar.button("🏠 最初の画面に戻る", use_container_width=True):
        st.session_state.analyzed = False
        st.session_state.start_pos = None
        st.session_state.end_pos = None
        st.rerun()

    # --- メイン画面の出力（地図や分析結果） ---
    st.title("✅ バリアフリー経路の解析結果")
    start_pos = st.session_state.start_pos
    end_pos = st.session_state.end_pos
    
    # ！！ここに前回の「道路ネットワーク構築〜地図描画」の処理をそのまま入れます！！
    # （※長いので省略しますが、前回の try: 以下の処理をここにコピペしてください）
    
    try:
        with st.spinner("安全なルートを計算しています..."):
            # 例: m = folium.Map(...) などの地図処理
            st.success(f"出発地({start_pos[0]:.4f}, {start_pos[1]:.4f}) から 目的地({end_pos[0]:.4f}, {end_pos[1]:.4f}) までのルートです。")
            # st_folium(m, width=900, height=550)
    except Exception as e:
        st.error(f"エラー: {e}")