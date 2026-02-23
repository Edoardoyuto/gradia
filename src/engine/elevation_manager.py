import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import osmnx as ox
from src.engine.elevation_query import ElevationQuery

class ElevationManager:
    def __init__(self, base_dir="data"):
        self.base_path = Path(base_dir)
        self.processed_dir = self.base_path / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        # 最終的な保存先
        self.enriched_path = self.processed_dir / "enriched_network.graphml"

    def get_elevation(self, lat, lon):
        with ElevationQuery(mode="api") as eq:
            return eq.get_elevation(lat, lon)

    def enrich_nodes_with_elevation(self, G):
        """
        ノードに標高を付与し、完了したら自動的にファイルへ保存する。
        """
        nodes = list(G.nodes(data=True))
        print(f"Enriching {len(nodes)} nodes with elevation data...")

        def fetch_task(node_data):
            node_id, data = node_data
            # すでに標高データがある場合はスキップ（効率化）
            if 'elevation' in data and data['elevation'] is not None:
                return
            elev = self.get_elevation(data['y'], data['x'])
            G.nodes[node_id]['elevation'] = elev

        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(fetch_task, nodes)

        print("Elevation enrichment complete.")
        
        # --- 自動保存処理を追加 ---
        ox.save_graphml(G, filepath=str(self.enriched_path))
        print(f"Successfully saved enriched network to {self.enriched_path}")
        
        return G

if __name__ == "__main__":
    from src.engine.network_fetcher import NetworkFetcher
    
    fetcher = NetworkFetcher()
    # 既存のネットワークをロード（なければダウンロード）
    G = fetcher.get_network(34.823, 135.770)
    
    manager = ElevationManager()
    # この一行で「取得・付与・保存」がすべて完結する
    G = manager.enrich_nodes_with_elevation(G)