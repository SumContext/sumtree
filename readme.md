
sumtree produces output similar to the tree command, but adds file 
summaries from LLMs next to each filename.

example:
```

$ sumtree ./
.
├── .git
├── cog_cfg.json
│ Defines project config: max file size, LLM names, supported types, gitignore patterns.
├── devShells.nix
│ Nix shell: custom Python (PyTorch Vulkan, stable-baselines3, Keras+Pillow) with Vulkan/OpenCL libs and Qt6.
├── flake.nix
│ Flake with Python 3.13 env, requests & pathspec, defines sumtree script, devShell includes env & script.
├── issue.md
│ #summary: Nix flake with custom Python env, Vulkan & Qt libs, shell command `sumtree`, and GPU dev tools.
├── readme.md
│ sumtree: tree-like output + LLM summaries writes tree.sums.json gignore filtering notes plans SumIssueSumFile.
└── sumtree.py
 Python script: scans directory, builds tree, caches file checksums, creates AI‑summaries of each file.

```

### Currently works!

`tree.sums.json` is produced in the target dir - saving summaries

in `cog_cfg.json` add gitignore style descriptions of files you don't want sent over the internet:

gignore json:

```json
    "gignore": ".git/\n*.key"
```

###

make sure you have a `cog_cfg.json` and `secret.key` in your `~/.config/sumtree/` directory


### installing to flake systems add the following 3 lines:

```
    ## add to inputs
    SumContext.url = "github:SumContext/sumtree/main";

    nixosConfigurations.nixos = nixpkgs.lib.nixosSystem { 
      system = "x86_64-linux";
      specialArgs = {
        # Pass unstable pkgs to configuration.nix if needed for system packages
        locked = nixpkgs-locked.legacyPackages."x86_64-linux";
        unstable = nixpkgs-unstable.legacyPackages."x86_64-linux";
        unstablelocked = nixpkgs-unstable-locked.legacyPackages."x86_64-linux";

        ## add this line if your configuration is a flake
        inherit (inputs) SumContext;

      };

environment.systemPackages = with pkgs; [

    ## add this to your pkgs
    SumContext.packages.${pkgs.system}.sumtree

```