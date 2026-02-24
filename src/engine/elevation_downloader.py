import math
import requests
import numpy as np
from PIL import Image
from io import BytesIO
import os
from pathlib import Path

class ElevationDownloader:
    def __init__(self, cache_dir="data/tiles"):
        self.base_url = "https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{x}/{y}.png"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def latlon_to_tile(self, lat, lon, z=15):
        x = int((lon + 180.0) / 360.0 * (2.0**z))
        y = int((1.0 - math.log(math.tan(math.radians(lat)) + (1.0 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * (2.0**z))
        return x, y

    def _tile_path(self, z, x, y):
        return self.cache_dir / f"{z}_{x}_{y}.npy"

    def _download_tile(self, z, x, y):
        url = self.base_url.format(z=z, x=x, y=y)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert('RGB')
        arr = np.array(img)
        np.save(self._tile_path(z, x, y), arr)
        return arr

    def _load_tile(self, z, x, y):
        path = self._tile_path(z, x, y)
        if path.exists():
            return np.load(path)
        return self._download_tile(z, x, y)

    def get_elevation_from_tile(self, lat, lon, z=15):
        tx, ty = self.latlon_to_tile(lat, lon, z)
        data = self._load_tile(z, tx, ty)

        lon_min = (tx / 2.0**z) * 360.0 - 180.0
        lon_max = ((tx + 1) / 2.0**z) * 360.0 - 180.0
        lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / 2.0**z))))
        lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + 1) / 2.0**z))))

        pixel_x = int((lon - lon_min) / (lon_max - lon_min) * 256)
        pixel_y = int((lat_max - lat) / (lat_max - lat_min) * 256)
        pixel_x = max(0, min(255, pixel_x))
        pixel_y = max(0, min(255, pixel_y))

        r, g, b = data[pixel_y, pixel_x].astype(float)
        x_val = r * 65536 + g * 256 + b
        return x_val * 0.01 if x_val < 8388608 else (x_val - 16777216) * 0.01