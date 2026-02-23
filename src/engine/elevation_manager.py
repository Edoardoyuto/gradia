import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from src.engine.elevation_query import ElevationQuery

class ElevationManager:
    def __init__(self, base_dir="data"):
        self.base_path = Path(base_dir)
        self.processed_dir = self.base_path / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        # キャッシュ用辞書
        self.elevation_cache = {}

    def get_elevation(self, lat, lon):
        """単一地点の標高取得"""
        with ElevationQuery(mode="api") as eq:
            return eq.get_elevation(lat, lon)

    def enrich_nodes_with_elevation(self, G):
        """
        OSMnxで取得したグラフ(G)の全ノードに標高を高速に付与する。
        並列処理（マルチスレッド）でAPIを叩くため、数千件でも数十秒で終わります。
        """
        nodes = list(G.nodes(data=True))
        print(f"Enriching {len(nodes)} nodes with elevation data...")

        def fetch_task(node_data):
            node_id, data = node_data
            # すでに標高があればスキップ
            if 'elevation' in data: return
            elev = self.get_elevation(data['y'], data['x'])
            G.nodes[node_id]['elevation'] = elev

        # 最大20スレッドで並列実行（速度とサーバー負荷のバランス）
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(fetch_task, nodes)

        print("Elevation enrichment complete.")
        return G

if __name__ == "__main__":
    from src.engine.network_fetcher import NetworkFetcher
    
    # 1. 道路ネットワークの取得 (Step 2で作成したもの)
    fetcher = NetworkFetcher()
    G = fetcher.get_network(34.823, 135.770)
    
    # 2. 標高の自動付与
    manager = ElevationManager()
    G = manager.enrich_nodes_with_elevation(G)
    
    # 3. 結果確認
    sample_node = list(G.nodes(data=True))[0]
    print(f"\nSample Node Data: {sample_node}")