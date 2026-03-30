from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent / 'services' / 'worker-tiktok' / 'scripts' / 'tiktok_oauth_auth.py'
runpy.run_path(str(TARGET), run_name='__main__')

