#!/usr/bin/env python3
# coding=utf-8
# Copyright (C) 2023-2026 Roy Pfund. All rights reserved.
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
import subprocess, threading, re, os, sys, inspect, shutil, argparse, random, math, json, fnmatch, requests, json, types, smart_open
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
    parser.add_argument("-v", "--verbose", action="store_true", help="Print Git revision")
    args = parser.parse_args()

    if args.verbose:
        print("Git revision:", os.environ.get("SUMTREE_GIT_REV", "unknown"))

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

# def Load_Plaintxt(file_path):
#     if not os.path.exists(file_path):
#         return None, f"Error: File {file_path} not found.", True
#     try:
#         with smart_open.open(file_path, "r", encoding="utf-8") as f:
#             content = f.read()
#         return content, None, False
#     except Exception as e:
#         return None, f"Error reading file: {str(e)}", True

def get_response(payload_builder, *builder_args):
    """
    Orchestrates config loading, and API calls.
    No awareness of builder_args, delegates to payload_builder
    """
    try:
        # Load Config
        with open(cog_cfg, "r", encoding="utf-8") as f:
            cfg = json.load(f, object_hook=lambda d: types.SimpleNamespace(**d))
        if not cfg.projectConfig.JuniorLLM or not cfg.projectConfig.API_URL:
            return "Configuration Error: Missing API_URL or Model name.", True
        # Build payload
        payload, err = payload_builder(cfg, *builder_args)
        if err:
            return payload, True
        # API Request
        headers = {
            "Authorization": f"Bearer {secret_k}",
            "Content-Type": "application/json"
        }
        response = requests.post(cfg.projectConfig.API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json(), False
    except FileNotFoundError:
        return f"Config file {cog_cfg} not found.", True
    except requests.exceptions.RequestException as e:
        return f"Network/API Error: {str(e)}", True
    except Exception as e:
        return f"Unexpected Error: {str(e)}", True

def get_sum(file_path, *builder_args):
    data, err = get_response(load_sum, file_path, *builder_args)
    if err:
        # data is already an error message string
        return data, True
    
    # Only try to parse JSON if there was no error
    try:
        message = data['choices'][0]['message']
        content = message.get('content', '').strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 2:
                content = "\n".join(lines[1:-1]).strip()
            else:
                content = content.replace("```", "").strip()
        return content, False
    except (KeyError, IndexError, TypeError) as e:
        return f"Error parsing JSON response: {str(e)}", True

def load_sum(cfg, *builder_args):
    model_name = cfg.projectConfig.JuniorLLM
    max_size = cfg.projectConfig.maxSupportedFileSize
    file_path = builder_args[0]
    try:
        if os.path.getsize(file_path) > max_size:
            return "(skipped: file too large)", True
    except Exception as e:
        return f"File size check failed: {str(e)}", True
    code_content, err = Load_Plaintxt(file_path)
    if err:
        return code_content, True
    extra_context = builder_args[0] if builder_args else "large project"
    prompt = "Provide a markdown code escaped 111 chars or less summary of this file."
    payload = {
        "model": model_name,
        "include_reasoning": True,
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
            "content": "```C program to calculate and display real or complex roots of a quadratic equation using coefficients.```",
            "reasoning": "The user requested a concise summary of a C program. The program reads coefficients of a quadratic equation, computes the determinant, and based on its value, calculates and prints either two real roots, one repeated real root, or two complex roots. The assistant generated a short summary that captures this functionality within the character limit."
          },
          {
            "role": "user",
            "content": f"{prompt}\n```\n{code_content}\n```\n"
          }
        ]
    }
    return payload, False

def Load_Plaintxt(file_path):
    """Utility to read file content safely."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found.", True
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read(), False
    except Exception as e:
        return f"Error reading file: {str(e)}", True

def load_ignore_patterns(dir_path: str):
    global cog_cfg  # <--- CRITICAL FIX: Access the global path resolved in main()
    
    patterns = ""
    # Use the global cog_cfg path instead of constructing a new one
    if cog_cfg and os.path.isfile(cog_cfg):
        try:
            with open(cog_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            patterns = cfg.get("projectConfig", {}).get("gignore", "")
        except Exception:
            pass
    # print(f"===patterns===\n{patterns}\n===patterns===")
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
            cached_sum = cached_entry.get("sum", "")
            # We reject the cache if the summary is too short (< 24), 
            # forcing the script to re-evaluate or re-generate it.
            if (cached_entry.get("time") and
                cached_entry["time"] >= mtime and
                not cached_entry.get("error", False) and
                len(cached_sum) >= 24):  # <--- NEW CHECK ADDED HERE
                entry["sum"] = cached_sum
                entry["time"] = cached_entry["time"]
                entry["error"] = cached_entry.get("error", False)
                use_cached = True

        if not use_cached:
            summary, is_error = get_sum(full_path)
            # Check if summary is less than 24 chars. 
            # If so, keep the summary text but mark error as True.
            if not is_error and len(summary) < 24:
                entry["sum"] = summary
                entry["error"] = True
            else:
                entry["sum"] = summary
                entry["error"] = is_error
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
