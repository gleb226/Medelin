import sys
import pathlib
import os

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from app.utils.paths import get_uploads_dir, get_cache_dir
    print("Paths import OK")
    print("Uploads dir:", get_uploads_dir())
    print("Cache dir:", get_cache_dir())
    
    from app.utils.photo_utils import process_photo
    print("Photo utils import OK")
    
    from app.utils.data_cache import public_data_cache
    print("Data cache import OK")
    
    import api
    print("API import OK")
    
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
