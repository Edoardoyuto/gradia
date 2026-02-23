import os
import subprocess
from pathlib import Path
from src.engine.elevation_query import ElevationQuery

class ElevationManager:
    def __init__(self, base_dir="data"):
        # プロジェクトルートからの相対パスを確実に扱う
        self.base_path = Path(base_dir)
        self.raw_dir = self.base_path / "raw"
        self.processed_dir = self.base_path / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.merged_tif = self.processed_dir / "merged_elevation.tif"

    def update_geotiff(self):
        """全てのXMLを結合して1つのGeoTIFFにする"""
        xml_files = list(self.raw_dir.glob("*.xml"))
        if not xml_files:
            print("Error: No XML files found in data/raw/")
            return False

        vrt_path = self.processed_dir / "temp.vrt"
        try:
            # 1. 仮想ファイル(VRT)の構築
            subprocess.run(["gdalbuildvrt", str(vrt_path)] + [str(f) for f in xml_files], check=True)
            # 2. 実体(GeoTIFF)への変換
            subprocess.run(["gdal_translate", str(vrt_path), str(self.merged_tif)], check=True)
            print(f"Success: {self.merged_tif} generated.")
            return True
        except Exception as e:
            print(f"GDAL Error: {e}")
            return False

    def get_elevation(self, lat, lon):
        """標高を取得する"""
        if not self.merged_tif.exists():
            if not self.update_geotiff():
                return None
            
        with ElevationQuery(str(self.merged_tif)) as eq:
            return eq.get_elevation(lat, lon)