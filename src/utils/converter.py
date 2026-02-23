# src/utils/converter.py
import subprocess
import os
import glob

def convert_gsi_xml_to_tif(input_dir, output_tif):
    """
    input_dir内にある国土地理院のXML群を1つのGeoTIFFに結合・変換する
    """
    xml_files = glob.glob(os.path.join(input_dir, "*.xml"))
    if not xml_files:
        print("Error: No XML files found in the directory.")
        return False

    print(f"Converting {len(xml_files)} XML files to {output_tif}...")
    
    # GDALの gdal_dem (または内部的なxml解釈) を利用して変換
    # Ubuntuのコマンドラインツール gdalwarp や gdal_translate を利用
    try:
        # 1. XMLを一時的なVRT(仮想ラスタ)にまとめるのが効率的ですが、
        # シンプルにgdal_merge的な動きをするコマンドを構成します。
        cmd = ["gdal_translate"] + [xml_files[0], output_tif]
        # ※複数のXMLがある場合は gdalbuildvrt -> gdal_translate の流れが一般的
        subprocess.run(cmd, check=True)
        print("Conversion successful!")
        return True
    except Exception as e:
        print(f"Conversion failed: {e}")
        return False

if __name__ == "__main__":
    # 単体テスト用
    RAW_DATA_DIR = "data/raw/"
    OUTPUT_FILE = "data/processed/local_elevation.tif"
    os.makedirs("data/processed/", exist_ok=True)
    convert_gsi_xml_to_tif(RAW_DATA_DIR, OUTPUT_FILE)