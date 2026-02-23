import requests

class ElevationQuery:
    def __init__(self, mode="api", tif_path=None):
        self.mode = mode
        # 緯度経度を直接受け取れる公式の標高API
        self.api_url = "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_elevation(self, lat, lon):
        """
        指定した(lat, lon)の標高を返す。
        """
        params = {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "outtype": "JSON"
        }
        
        try:
            # 緯度経度をパラメータとして送信
            response = requests.get(self.api_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                elevation = data.get("elevation")
                
                # 有効な数値であればfloatで返す
                if elevation is not None and isinstance(elevation, (int, float)):
                    return float(elevation)
                elif isinstance(elevation, str) and elevation != "-----":
                    return float(elevation)
                return None
            else:
                print(f"API Error: Status code {response.status_code}")
                return None
                
        except Exception as e:
            print(f"API Connection error: {e}")
            return None

if __name__ == "__main__":
    with ElevationQuery(mode="api") as eq:
        # 同志社大学付近
        test_lat, test_lon = 34.823, 135.770 
        result = eq.get_elevation(test_lat, test_lon)
        
        print("--- Elevation API Test (Direct Endpoint) ---")
        if result is not None:
            print(f"Elevation: {result}m")
        else:
            print("Failed to retrieve data. Check connection.")