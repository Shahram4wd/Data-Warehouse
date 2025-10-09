# agents/tools.py
from google.adk.tools import FunctionTool
import os, subprocess, json, glob

def read_files(glob_pattern: str, max_kb: int = 96) -> dict:
    paths = [p for p in glob.glob(glob_pattern, recursive=True) if os.path.isfile(p)]
    out = {}
    for p in paths[:200]:
        with open(p, "r", errors="ignore") as f:
            out[p] = f.read()[:max_kb*1024]
    return out

def write_text(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: f.write(content)
    return path

def run_tests(args: list[str] | None = None) -> dict:
    cmd = ["docker","compose","run","--rm","tests","pytest","-q"] + (args or [])
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"ok": res.returncode==0, "stdout": res.stdout, "stderr": res.stderr}

ReadFiles = FunctionTool(func=read_files)
WriteText = FunctionTool(func=write_text)
RunTests  = FunctionTool(func=run_tests)
