# src/engine/grade_calculator.py

import networkx as nx

class GradeCalculator:
    def __init__(self):
        # ペナルティ係数をここで管理すると、後で調整しやすくなります
        self.alpha = 1000  # 上りのしんどさ
        self.beta = 20     # 下りの怖さ

    def add_effort_weights(self, G):
        """
        全エッジに対して、車いすユーザー向けの移動コスト(effort)を計算する
        """
        # 上りと下りを区別するため有向グラフに変換
        if not G.is_directed():
            G = G.to_directed()

        for u, v, key, data in G.edges(keys=True, data=True):
            # 1. 距離の取得（ゼロ除算防止）
            length = max(data.get('length', 1.0), 0.1)
            
            # 2. 標高の取得
            elev_u = G.nodes[u].get('elevation')
            elev_v = G.nodes[v].get('elevation')
            
            if elev_u is None or elev_v is None:
                # 標高不明な道は、少しだけコストを高くして「避ける」傾向に
                effort = length * 1.2
                slope = 0
            else:
                # 3. 勾配の計算
                slope = (elev_v - elev_u) / length
                
                # 4. ペナルティ係数の計算ロジック
                if abs(slope) > 0.1: # 10%超えは実質通行不可
                    effort = length * 100
                elif slope > 0.02:   # 2%超えの上り
                    effort = length * (1.0 + self.alpha * (slope ** 2))
                elif slope < -0.02:  # 2%超えの下り
                    effort = length * (1.0 + self.beta * abs(slope))
                else:                # 平坦
                    effort = length
            
            # 属性として保存
            G.edges[u, v, key]['slope'] = slope
            G.edges[u, v, key]['effort'] = effort
            
        return G