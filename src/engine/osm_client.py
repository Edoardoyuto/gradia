import osmnx as ox
import os
from pathlib import Path

class OSMClient: 
    def __init__(self, data_dir="data/networks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_network(self, lat, lon, dist=3000, network_type="walk"):
        """
        指定座標から半径distメートルの道路ネットワークを取得。
        キャッシュがあればそこから読み込み、なければダウンロード。
        """
        filename = self.data_dir / f"network_{round(lat,3)}_{round(lon,3)}_{dist}m.graphml"
        
        if filename.exists():
            print(f"Loading cached network: {filename}")
            return ox.load_graphml(filename)
        
        print(f"Downloading network from OSM (radius: {dist}m)...")
        G = ox.graph_from_point((lat, lon), dist=dist, network_type=network_type)
        
        # 保存
        ox.save_graphml(G, filepath=filename)
        print(f"Network saved to {filename}")
        return G

if __name__ == "__main__":
    print("--- Testing Network Fetcher ---")
    fetcher = NetworkFetcher()
    # 同志社大学 京田辺キャンパス付近
    G = fetcher.get_network(34.823, 135.770)
    
    print(f"Number of nodes: {len(G.nodes)}")
    print(f"Number of edges: {len(G.edges)}")