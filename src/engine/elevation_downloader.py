import math
import requests
import numpy as np
from PIL import Image
from io import BytesIO

class ElevationDownloader:
    def __init__(self):
        # 国土地理院 標高タイル (DEM5A)
        self.base_url = "https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{x}/{y}.png"

    def latlon_to_tile(self, lat, lon, z=15):
        """緯度経度をタイル座標(x, y)に変換"""
        x = int((lon + 180.0) / 360.0 * (2.0**z))
        y = int((1.0 - math.log(math.tan(math.radians(lat)) + (1.0 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * (2.0**z))
        return x, y

    def get_elevation_from_tile(self, lat, lon, z=15):
        """
        指定した座標を含むタイルを1枚ダウンロードし、標高データを取得する。
        通信を1回に集約するための核心部。
        """
        x, y = self.latlon_to_tile(lat, lon, z)
        url = self.base_url.format(z=z, x=x, y=y)
        
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            
            # PNG画像を読み込み
            img = Image.open(BytesIO(resp.content)).convert('RGB')
            data = np.array(img)
            
            # タイル内のピクセル位置を特定
            # タイルは256x256ピクセル
            lon_min = (x / 2.0**z) * 360.0 - 180.0
            lon_max = ((x + 1) / 2.0**z) * 360.0 - 180.0
            lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / 2.0**z))))
            lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / 2.0**z))))
            
            pixel_x = int((lon - lon_min) / (lon_max - lon_min) * 256)
            pixel_y = int((lat_max - lat) / (lat_max - lat_min) * 256)
            
            # ピクセル位置が範囲外にならないよう調整
            pixel_x = max(0, min(255, pixel_x))
            pixel_y = max(0, min(255, pixel_y))
            
            # 国土地理院の標高計算公式
            # x = 2^16R + 2^8G + B
            # h < 2^23 の場合: h = x * 0.01
            # h >= 2^23 の場合: h = (x - 2^24) * 0.01 (負の値/海域)
            r, g, b = data[pixel_y, pixel_x].astype(float)
            x_val = r * 65536 + g * 256 + b
            
            if x_val < 8388608:
                h = x_val * 0.01
            else:
                h = (x_val - 16777216) * 0.01
                
            return h

        except Exception as e:
            print(f"Error downloading tile: {e}")
            return None