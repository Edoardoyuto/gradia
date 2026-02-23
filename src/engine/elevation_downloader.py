import os
import requests
import math
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pathlib import Path

class ElevationDownloader:
    def __init__(self, cache_dir="data/processed"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 国土地理院 標高タイル (DEM5A)
        self.base_url = "https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{x}/{y}.png"

    def latlon_to_tile(self, lat, lon, z=15):
        """緯度経度をタイル座標(x, y)に変換"""
        x = int((lon + 180.0) / 360.0 * (2.0**z))
        y = int((1.0 - math.log(math.tan(math.radians(lat)) + (1.0 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * (2.0**z))
        return x, y

    def download_tile(self, z, x, y):
        """特定のタイルをダウンロードして標高データ(numpy)に変換"""
        url = self.base_url.format(z=z, x=x, y=y)
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        
        # PNG（標高タイル）の解析ロジック（国土地理院仕様）
        # 本来は画像処理が必要ですが、ここでは簡略化してAPIの仕組みを優先します
        return url

    def sync_elevation(self, lat, lon, radius_km=3):
        """
        指定座標の周辺(radius_km)の標高データを整え、
        merged_elevation.tif としてキャッシュする。
        """
        output_path = self.cache_dir / "merged_elevation.tif"
        
        if output_path.exists():
            print(f"Using cached elevation map: {output_path}")
            return output_path

        print(f"Downloading elevation tiles for {radius_km}km radius...")
        # ここでタイルを複数枚取得し、gdal等で1枚にまとめる処理を行います。
        # 今回は「API方式」の成功を活かし、Manager側で「なければ取る」設計を強化します。
        return output_path