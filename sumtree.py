#!/usr/bin/env python3
# coding=utf-8
#
# Permission is  hereby  granted,  free  of  charge,  to  any  person
# obtaining a copy of  this  software  and  associated  documentation
# files  (the  "Software"),  to  deal   in   the   Software   without
# restriction, including without limitation the rights to use,  copy,
# modify, merge, publish, distribute, sublicense, and/or sell  copies
# of the Software, and to permit persons  to  whom  the  Software  is
# furnished to do so.
#
# The above copyright notice and  this  permission  notice  shall  be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT  WARRANTY  OF  ANY  KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  OF
# MERCHANTABILITY,   FITNESS   FOR   A   PARTICULAR    PURPOSE    AND
# NONINFRINGEMENT.  IN  NO  EVENT  SHALL  THE  AUTHORS  OR  COPYRIGHT
# OWNER(S) BE LIABLE FOR  ANY  CLAIM,  DAMAGES  OR  OTHER  LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING  FROM,
# OUT OF OR IN CONNECTION WITH THE  SOFTWARE  OR  THE  USE  OR  OTHER
# DEALINGS IN THE SOFTWARE.
#
######################################################################

from datetime import datetime, timezone
import pathspec
import subprocess, threading, re, os, sys, inspect, shutil, argparse, random, math, json, fnmatch, requests
rows, columns = os.popen('stty size', 'r').read().split() #http://goo.gl/cD4CFf
#"pydoc -p 1234" will start a HTTP server on port 1234, allowing you to browse
#the documentation at "http://localhost:1234/" in your preferred Web browser.
cwf = os.path.abspath(inspect.getfile(inspect.currentframe())) # Current Working File
cwfd = os.path.dirname(cwf) # Current Working File Path

# from openai import OpenAI
# Read the secret key from the file
    # client = OpenAI( base_url="https://openrouter.ai/api/v1",
    #     api_key= f.read().strip(), )

# Global variables (initialized to None; set in main())
treesums = None
cog_cfg = None
secret_k = None

def main():
    global treesums, cog_cfg, secret_k  # Declare to modify globals

    parser = argparse.ArgumentParser(description="Generate JSON tree of a directory.")
    parser.add_argument("directory", help="Path to the directory")
    args = parser.parse_args()
    script_dir = args.directory
    treesums = os.path.join(script_dir, "tree.sums.json")  # Fixed dir_path -> script_dir

    # Define config directory in home
    home_cfg_dir = os.path.join(os.path.expanduser("~"), ".config", "sumtree")

    # Prefer ~/.config/sumtree, fallback to script_dir
    cog_cfg = os.path.join(home_cfg_dir, "cog_cfg.json") \
        if os.path.exists(os.path.join(home_cfg_dir, "cog_cfg.json")) \
        else os.path.join(script_dir, "cog_cfg.json")
    # print(cog_cfg)
    
    secretkey = os.path.join(home_cfg_dir, "secret.key") \
        if os.path.exists(os.path.join(home_cfg_dir, "secret.key")) \
        else os.path.join(script_dir, "secret.key")
    # print(secretkey)

    with open(secretkey, "r") as f:
        secret_k = f.read().strip()

    flist = flistwithsums(ftree2sums(dir2tree_data(script_dir)), args.directory)
    print(ftree2bashsumtree(script_dir))

    # ftree = dir2tree_data(script_dir)
    # # print(json.dumps(ftree, indent=2))
    # flist = ftree2sums(ftree)
    # # print(ftree2bashtree(ftree))
    # 
    # # readm = os.path.join(script_dir, "readme.md")
    # # print(file2sum(readm))
    # # file2sum tested working
    # 
    # # # enrich with summaries (using cache if available)
    # flist = flistwithsums(flist, args.directory)
    # # print(json.dumps(flist, indent=2))

def file2sum(file_path):
    # 1. Validate Input
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found.", True # <--- CHANGED (Added True)
    # 2. Load File Content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code_content = f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}", True # <--- CHANGED (Added True)
    # 3. Load Config (for Model Name)
    # We look for cog_cfg.json in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(script_dir, "cog_cfg.json")
    model_name = "openai/gpt-oss-20b:free" # Default fallback
   
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r') as f:
                cfg = json.load(f)
                # navigate: projectConfig -> JuniorLLM
                model_name = cfg.get("projectConfig", {}).get("JuniorLLM", model_name)
        except:
            pass # keep default if config fails
    # 4. Prepare API Call
    requests_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {secret_k}",
        "Content-Type": "application/json"
    }
    # We ask the model to include reasoning and keep it short
    prompt = "Provide a markdown code escaped 111 chars or less summary of this file."
    payload = {
        "model": model_name,
        "include_reasoning": True, # Required for some models to output the 'reasoning' field
        "messages": [
          {
            "role": "system",
            "content": "role: you are a junior level engineer, preparing short summaries of files in a large project"
          },
          {
            "role": "user",
            "content": "in 111 chars or less summarize the following file:\n```\n#include<stdio.h>\n#include<math.h>\n\nint main() {\n    float a, b, c, determinant, r1, r2, real, imag;\n    printf(\"\\n\\nEnter coefficients a, b and c: \\n\\n\\n\");\n    scanf(\"%f%f%f\", &a, &b, &c);\n\n    determinant == b*b - 4*a*c; \n    if (determinant > 0) {\n        r1 = (-b + sqrt(determinant))/2*a;\n        r2 = (-b - sqrt(determinant))/2*a;\n        printf(\"\\n\\n\\nRoots are: %.2f and %.2f \", r1, r2);\n    } else if (determinant == 0) {  \n        r1 = r2 = -b/(2*a);\n        printf(\"\\n\\n\\nRoots are: %.2f and %.2f \", r1, r2);\n    } else {\n        real = -b/(2*a);\n        imag = sqrt(-determinant)/(2*a);\n        printf(\"\\n\\n\\nRoots are %.2f + i%.2f and %.2f - i%.2f \", real, imag, real, imag);\n    }\n    return 0;\n}\n```"
          },
          {
            "role": "assistant",
            "content": "summary:\n\n```C program to calculate and display real or complex roots of a quadratic equation using coefficients.```",
            "reasoning": "The user requested a concise summary of a C program. The program reads coefficients of a quadratic equation, computes the determinant, and based on its value, calculates and prints either two real roots, one repeated real root, or two complex roots. The assistant generated a short summary that captures this functionality within the character limit."
          },
            {"role": "user", "content": f"File: {os.path.basename(file_path)}\n\nContent:\n{code_content}\n\n{prompt}"}
        ]
    }
    # 5. Execute Request
    try:
        response = requests.post(requests_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"API Error: {str(e)}", True # <--- CHANGED (Added True)
    # 6. Parse and Format Output
    try:
        # Extract the assistant's message
        message = data['choices'][0]['message']
        content = message.get('content', '').strip()
        # Trim markdown fences if present
        if content.startswith("```") and content.endswith("```"):
            lines = content.splitlines()
            if len(lines) >= 2:
                content = "\n".join(lines[1:-1]).strip()
        return content, False # <--- CHANGED (Added False)
    except (KeyError, IndexError) as e:
        return f"Error parsing JSON response: {str(e)}", True # <--- CHANGED (Added True)

# def load_ignore_patterns(dir_path: str):
#     cfg_file = os.path.join(dir_path, "cog_cfg.json")
#     patterns = []
#     if os.path.isfile(cfg_file):
#         try:
#             with open(cfg_file, "r", encoding="utf-8") as f:
#                 cfg = json.load(f)
#             gignore_str = cfg.get("projectConfig", {}).get("gignore", "")
#             if isinstance(gignore_str, str):
#                 # split on newlines, strip whitespace
#                 patterns = [p.strip() for p in gignore_str.splitlines() if p.strip()]
#         except Exception:
#             pass
#     return patterns
# 
# def should_ignore(name: str, full_path: str, patterns: list) -> bool:
#     for pat in patterns:
#         # directory ignore (like ".git/")
#         if pat.endswith("/") and name == pat.rstrip("/"):
#             return True
#         # glob-style ignore
#         if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(full_path, pat):
#             return True
#     return False

def load_ignore_patterns(dir_path: str):
    cfg_file = os.path.join(dir_path, "cog_cfg.json")
    patterns = ""
    if os.path.isfile(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            patterns = cfg.get("projectConfig", {}).get("gignore", "")
        except Exception:
            pass
    # Compile patterns using GitWildMatchPattern (same rules as .gitignore)
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns.splitlines())

def should_ignore(name: str, full_path: str, spec) -> bool:
    # spec.match_file expects a relative path
    rel_path = os.path.relpath(full_path)
    return spec.match_file(rel_path)

def dir2tree_data(dir_path: str) -> dict:
    forbidden_pattern = re.compile(r'[<>:"|?*\x00]')
    is_valid_path = isinstance(dir_path, str) and len(dir_path.strip()) > 0 and not forbidden_pattern.search(dir_path)
    if not is_valid_path or not os.path.isdir(dir_path):
        return {
            "name": dir_path,
            "is_dir": False,
            "children": [],
            "is_valid_path": is_valid_path,
            "path_exists": os.path.isdir(dir_path)
        }
    ignore_spec = load_ignore_patterns(dir_path)

    def build_tree(path: str) -> dict:
        name = os.path.basename(path) or path
        node = {
            "name": name,
            "is_dir": os.path.isdir(path),
            "children": []
        }
        if node["is_dir"]:
            try:
                for entry in os.listdir(path):
                    full_path = os.path.join(path, entry)
                    if should_ignore(entry, full_path, ignore_spec):
                        continue
                    node["children"].append(build_tree(full_path))
            except PermissionError:
                pass
        return node

    file_tree = build_tree(dir_path)
    file_tree["is_valid_path"] = True
    file_tree["path_exists"] = True
    return file_tree

def ftree2bashtree(ftree):
    """
    Convert a file tree dict into a bash-style tree output string.
    """
    def recurse(node, prefix="", last=True):
        lines = []
        connector = "└── " if last else "├── "
        lines.append(prefix + connector + node["name"])
        if node.get("is_dir", False):
            children = sorted(node["children"], key=lambda x: x["name"])
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                new_prefix = prefix + (" " if last else "│ ")
                lines.extend(recurse(child, new_prefix, is_last))
        return lines
    lines = ["."]
    if ftree.get("is_dir", False):
        children = sorted(ftree["children"], key=lambda x: x["name"])
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            lines.extend(recurse(child, "", is_last))
    return "\n".join(lines)

def ftree2sums(ftree, parent_path=""):
    """
    Convert a file tree dict into a flat list of file entries.
    Only includes files, not directories.
    """
    files = []
    current_path = os.path.join(parent_path, ftree["name"])
    if ftree.get("is_dir", False):
        for child in ftree.get("children", []):
            files.extend(ftree2sums(child, current_path))
    else:
        rel_path = os.path.normpath(current_path)
        if not rel_path.startswith("./"):
            rel_path = "./" + rel_path.lstrip("./")
        files.append({
            "name": rel_path,
            "sum": False,
            "time": False,
            "error": False # <--- ADDED
        })
    return files

def flistwithsums(flist, dir_path: str):
    """
    Update flist with summaries for each file.
    Uses tree.sums.json if available for cached results.
    """
    sums_path = treesums
    cached = {}
    if os.path.isfile(sums_path):
        try:
            with open(sums_path, "r", encoding="utf-8") as f:
                cached_list = json.load(f)
                # convert to dict keyed by name
                cached = {entry["name"]: entry for entry in cached_list}
        except Exception:
            pass
    updated = []
    for entry in flist:
        fname = entry["name"]
        full_path = os.path.join(dir_path, fname.lstrip("./"))
        mtime = os.path.getmtime(full_path) if os.path.isfile(full_path) else 0
        use_cached = False
        if fname in cached:
            cached_entry = cached[fname]
            # MODIFIED: Check if time is valid AND ensure the previous entry was not an error
            if (cached_entry.get("time") and
                cached_entry["time"] >= mtime and
                not cached_entry.get("error", False)):
               
                # cached summary is newer and valid
                entry["sum"] = cached_entry["sum"]
                entry["time"] = cached_entry["time"]
                entry["error"] = cached_entry.get("error", False)
                use_cached = True
        if not use_cached:
            summary, is_error = file2sum(full_path)
            entry["sum"] = summary
            entry["error"] = is_error
            # MODIFIED: Explicit UTC timestamp
            entry["time"] = int(datetime.now(timezone.utc).timestamp())
        updated.append(entry)
    # Save updated list back to tree.sums.json
    try:
        with open(sums_path, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save sums file: {e}")
    return updated

def ftree2bashsumtree(dir_path):
    """
    Convert a file tree dict into a bash-style tree output string with summaries.
    """
    ftree = dir2tree_data(dir_path)
    # 1. Get flat list of files to fetch/verify sums (uses cache via flistwithsums)
    raw_list = ftree2sums(ftree)
    sums_list = flistwithsums(raw_list, dir_path)
   
    # 2. Create a lookup map: { "./relative/path": "Summary text" }
    sum_map = {item['name']: item.get('sum', '') for item in sums_list}
    def get_summary(path):
        # Normalize path to match keys in sum_map (e.g., ensure ./ prefix)
        rel = os.path.normpath(path)
        if not rel.startswith("./"):
            rel = "./" + rel.lstrip("./")
        return sum_map.get(rel, "")
    def recurse(node, prefix="", last=True, parent_path=""):
        lines = []
        connector = "└── " if last else "├── "
       
        # Construct path for lookup
        current_path = os.path.join(parent_path, node["name"])
       
        # Add the tree line (same as ftree2bashtree)
        lines.append(prefix + connector + node["name"])
       
        # Add Summary (if it's a file)
        if not node.get("is_dir", False):
            summary = get_summary(current_path)
            if summary:
                # Indentation: if file used ├── (last=False), desc needs │
                # if file used └── (last=True), desc needs
                desc_prefix = prefix + (" " if last else "│ ")
                lines.append(f"{desc_prefix}{summary}")
        # Recurse children (same as ftree2bashtree)
        if node.get("is_dir", False):
            children = sorted(node["children"], key=lambda x: x["name"])
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                new_prefix = prefix + (" " if last else "│ ")
                lines.extend(recurse(child, new_prefix, is_last, current_path))
        return lines
    # Root execution
    lines = ["."]
    if ftree.get("is_dir", False):
        children = sorted(ftree["children"], key=lambda x: x["name"])
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            # Start recursion with empty parent_path so os.path.join works correctly
            lines.extend(recurse(child, "", is_last, ""))
    return "\n".join(lines)

if __name__ == "__main__":
    main()
