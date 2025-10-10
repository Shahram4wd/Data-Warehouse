# agents/tools.py
from google.adk.tools import FunctionTool
import os, subprocess, json, glob
from typing import Dict, List, Optional, Union

def read_files(glob_pattern: str, max_kb: int = 96) -> Dict[str, str]:
    """Read files matching a glob pattern"""
    paths = [p for p in glob.glob(glob_pattern, recursive=True) if os.path.isfile(p)]
    out = {}
    for p in paths[:200]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()[:max_kb*1024]
                out[p] = content
        except Exception as e:
            out[p] = f"Error reading file: {str(e)}"
    return out

def read_single_file(file_path: str, max_kb: int = 96) -> str:
    """Read a single file"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:max_kb*1024]
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_text(path: str, content: str) -> str:
    """Write text content to a file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: 
        f.write(content)
    return path

def run_tests(args: Optional[List[str]] = None) -> Dict[str, Union[bool, str]]:
    """Run tests using docker compose"""
    if args is None:
        args = []
    cmd = ["docker","compose","run","--rm","tests","pytest","-q"] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"ok": res.returncode==0, "stdout": res.stdout, "stderr": res.stderr}

# Create tool instances
ReadFiles = FunctionTool(func=read_files, name="read_files")
ReadSingleFile = FunctionTool(func=read_single_file, name="read_single_file")  
WriteText = FunctionTool(func=write_text, name="write_text")
RunTests = FunctionTool(func=run_tests, name="run_tests")

# Export all tools
__all__ = ["ReadFiles", "ReadSingleFile", "WriteText", "RunTests", "read_files", "read_single_file", "write_text", "run_tests"]
