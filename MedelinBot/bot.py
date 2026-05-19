
import sys

import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:

    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":

    import asyncio

    from main import run

    asyncio.run(run())
