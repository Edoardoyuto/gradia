# src/engine/elevation_query.py
import rasterio

class ElevationQuery:
    def __init__(self, tif_path):
        self.tif_path = tif_path
        self.dataset = None

    def __enter__(self):
        self.dataset = rasterio.open(self.tif_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dataset:
            self.dataset.close()

    def get_elevation(self, lat, lon):
        """
        指定した(lat, lon)の標高を返す。データがない場合はNone。
        """
        if not self.dataset:
            self.dataset = rasterio.open(self.tif_path)
            
        # rasterioのsampleメソッドは (longitude, latitude) の順
        coords = [(lon, lat)]
        try:
            for val in self.dataset.sample(coords):
                elev = val[0]
                # 国土地理院の無効値（-9999など）をチェック
                return elev if elev > -100 else None
        except Exception as e:
            print(f"Sampling error at {lat}, {lon}: {e}")
            return None

if __name__ == "__main__":
    # 単体テスト用（変換後のTIFがある前提）
    TIF_PATH = "data/processed/local_elevation.tif"
    try:
        with ElevationQuery(TIF_PATH) as eq:
            # 京田辺市近辺のダミー座標でテスト
            test_lat, test_lon = 34.82, 135.77 
            result = eq.get_elevation(test_lat, test_lon)
            print(f"Elevation at ({test_lat}, {test_lon}): {result}m")
    except Exception as e:
        print("TIF file not found. Please run converter.py first.")