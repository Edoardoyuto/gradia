import osmnx as ox
from src.engine.elevation_downloader import ElevationDownloader

# 高速なKumi Systemsのサーバーを使用
ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"
# タイムアウトによるエラーを防ぐ
ox.settings.timeout = 180

class ElevationManager:

    def __init__(self):
        # インスタンスを保持し、内部の tile_cache を活かす
        self.downloader = ElevationDownloader()

    def enrich_nodes_with_elevation(self, G):
        nodes = list(G.nodes(data=True))
        
        # 進行状況を出すと安心感があります
        print(f"Enriching {len(nodes)} nodes using cached tiles...")

        for node_id, data in nodes:
            # downloader内部で自動的に tile_cache が効くようになります
            elev = self.downloader.get_elevation_from_tile(data['y'], data['x'])
            G.nodes[node_id]['elevation'] = elev
            
        return G