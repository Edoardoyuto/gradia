import osmnx as ox
import streamlit as st
from geopy.distance import geodesic

@st.cache_data(show_spinner=False)
def get_walk_network(start_coords, end_coords):
    """
    出発地と目的地の座標から、両地点をカバーする歩行者用道路ネットワークを取得する。
    """
    # 1. 2つの地点の「中心座標」を計算する
    center_lat = (start_coords[0] + end_coords[0]) / 2.0
    center_lng = (start_coords[1] + end_coords[1]) / 2.0
    center_coords = (center_lat, center_lng)
    
    # バッファー距離を設定
    Buffer_dist = 500

    # 2. 2点間の直線距離（メートル）を計算する
    dist_m = geodesic(start_coords, end_coords).meters

    # 3. 取得する半径を決める（直線距離の半分 ＋ 500mの余裕を持たせる）
    # ※ 余裕（バッファ）がないと、遠回りするルートが範囲外になって計算できなくなります
    radius = (dist_m / 2) + Buffer_dist

    # 4. OpenStreetMapからグラフデータを取得
    # network_type='walk' で歩行者用の道（階段や細い路地含む）のみを抽出
    G = ox.graph_from_point(center_coords, dist=radius, network_type='walk')

    return G