


### Currently works!

`ftree2bashsumtree()`

`ftree2bashtree()`

`flistwithsums()`

`file2sum()`

`dir2tree_data()` looks in the top level of `dir_path` for a file `cog_cfg.json` and parse for a `gignore` var containing a `.gitignore` style list of files and dirs to ignore and ignore them.

gignore json:

```json
    "gignore": ".git/\n*.key"
```

### Why this works:
- `.git/` → ensures the entire Git directory is ignored.
- `*.key` → ignores any file ending in `.key`.
- Stored as a single string with newline separators, so later we can split and feed it into a glob matcher.

This way, our config mirrors the semantics of a real `.gitignore` file.
