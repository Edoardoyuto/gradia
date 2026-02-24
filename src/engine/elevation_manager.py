import osmnx as ox
from src.engine.elevation_downloader import ElevationDownloader

class ElevationManager:
    def __init__(self):
        self.downloader = ElevationDownloader()

    def enrich_nodes_with_elevation(self, G):
        nodes = list(G.nodes(data=True))
        # 通信が発生するのは最初の数回（タイルの枚数分）だけになる
        for node_id, data in nodes:
            elev = self.downloader.get_elevation_from_tile(data['y'], data['x'])
            G.nodes[node_id]['elevation'] = elev
        return G