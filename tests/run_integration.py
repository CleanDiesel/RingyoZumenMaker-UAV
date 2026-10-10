import importlib.util
import runpy
import sys
import traceback
from pathlib import Path

try:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "RingyoZumenMaker", root / "__init__.py", submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    runpy.run_path(sys.argv[1], run_name="__main__")
except BaseException:
    print(traceback.format_exc(), flush=True)
    sys.exit(1)
