# agents/tools.py
from google.adk.tools import FunctionTool
import os
import subprocess
import json
import glob

def read_files(glob_pattern, max_kb=96):
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

def read_single_file(file_path, max_kb=96):
    """Read a single file"""
    # Validate path is not empty
    if not file_path or not file_path.strip():
        return "Error: Empty file path provided"
    
    # Handle relative paths from agents directory to project root
    if file_path.startswith("ingestion/") or file_path.startswith("docs/") or file_path.startswith("scripts/"):
        file_path = os.path.join("..", file_path)
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()[:max_kb*1024]
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_text(path, content):
    """Write text content to a file"""
    # Validate path is not empty
    if not path or not path.strip():
        return "Error: Empty file path provided"
    
    # Handle relative paths from agents directory to project root
    if path.startswith("ingestion/") or path.startswith("docs/") or path.startswith("scripts/"):
        # If path looks like a project file, go up one directory to project root
        path = os.path.join("..", path)
    
    # Get directory path and handle edge cases
    dir_path = os.path.dirname(path)
    if dir_path:  # Only create directory if dirname is not empty
        os.makedirs(dir_path, exist_ok=True)
    
    try:
        with open(path, "w", encoding="utf-8") as f: 
            f.write(content)
        return os.path.abspath(path)
    except Exception as e:
        return f"Error writing file: {str(e)}"

def run_tests(args=None):
    """Run tests using docker compose"""
    if args is None:
        args = []
    cmd = ["docker", "compose", "run", "--rm", "tests", "pytest", "-q"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0, 
        "stdout": result.stdout, 
        "stderr": result.stderr
    }

# Create tool instances
ReadFiles = FunctionTool(func=read_files, name="read_files")
ReadSingleFile = FunctionTool(func=read_single_file, name="read_single_file")  
WriteText = FunctionTool(func=write_text, name="write_text")
RunTests = FunctionTool(func=run_tests, name="run_tests")

# Export all tools
__all__ = [
    "ReadFiles", 
    "ReadSingleFile", 
    "WriteText", 
    "RunTests", 
    "read_files", 
    "read_single_file", 
    "write_text", 
    "run_tests"
]
