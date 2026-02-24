import osmnx as ox
import streamlit as st
from geopy.distance import geodesic
# 正しいクラス名をインポート
from src.engine.osm_client import OSMClient

@st.cache_data(show_spinner=False)
def get_walk_network(start_coords, end_coords):
    """
    OSMClientを利用して、2点間をカバーする道路ネットワークをキャッシュ付きで取得する。
    """
    # 1. 2つの地点の中心座標を計算
    center_lat = (start_coords[0] + end_coords[0]) / 2.0
    center_lng = (start_coords[1] + end_coords[1]) / 2.0
    
    # 2. 2点間の直線距離（メートル）を計算
    dist_m = geodesic(start_coords, end_coords).meters
    
    # 3. 取得する半径を決定（バッファ 500m を追加）
    radius = (dist_m / 2) + 250

    # 4. OSMClientを使って取得（ここを NetworkFetcher から修正）
    client = OSMClient(data_dir="data/networks") 
    
    # メソッドを呼び出し
    G = client.get_network(
        lat=center_lat, 
        lon=center_lng, 
        dist=radius, 
        network_type='walk'
    )

    return G