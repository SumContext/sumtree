# devShells.nix
{ pkgs ? import <nixpkgs> {} }:

let
  # 1. Define a custom Python instance with OVERRIDES.
  myPython = pkgs.python312.override {
    packageOverrides = final: prev: {
      # Existing overrides...
      torch = prev.torch.override { vulkanSupport = true; };

      stable-baselines3 = prev.stable-baselines3.overridePythonAttrs (old: {
        doCheck = false; 
      });

      # New override for Keras: Add pillow to checkInputs to fix test failures
      keras = prev.keras.overridePythonAttrs (old: rec {
        checkInputs = (old.checkInputs or []) ++ [ final.pillow ];
      });
    };
  };

  # 2. Create the environment using the CUSTOM python instance
  myPythonEnv = myPython.withPackages (ps: [
    ps.torch 
    ps.pyside6
    ps.shiboken6
    ps.matplotlib
    ps.numpy
    ps.opencv-python
    ps.stable-baselines3
    ps.tqdm
    ps.ale-py
    ps.gymnasium
    # Add pillow for runtime image utils (e.g., if dqn.py or other code needs PIL)
    ps.pillow
    ps.tinygrad
    ps.openai
    ps.pydantic
    ps.requests
  ]);

in pkgs.mkShell {
  packages = [
    # The consolidated Python environment
    myPythonEnv
    # System Libraries for Vulkan (Required for the backend to find drivers)
    pkgs.vulkan-loader
    pkgs.vulkan-headers
    pkgs.vulkan-tools
    pkgs.vulkan-validation-layers

    # AMD/OpenCL Drivers
    pkgs.rocmPackages.clr
    pkgs.rocmPackages.rocm-smi
    pkgs.ocl-icd
    pkgs.opencl-headers
    pkgs.clinfo

    # Dev Tools
    pkgs.ruff
    pkgs.uv
    pkgs.cmake
    pkgs.SDL2
    pkgs.wayland
    pkgs.libxkbcommon
    pkgs.pulseaudio
    pkgs.xorg.libXcomposite

    # Qt6 components
    pkgs.kdePackages.qtbase
    pkgs.kdePackages.qtdeclarative
    pkgs.kdePackages.qtsvg
    pkgs.kdePackages.qttools
    pkgs.kdePackages.qtmultimedia
    pkgs.kdePackages.qtvirtualkeyboard
    pkgs.kdePackages.qt3d
  ];

  shellHook = ''
    if [[ $- == *i* ]]; then
      export PS1="[nix-vulkan:\w] "
    fi

    # FIX: Ensure PyTorch can find the Vulkan loader at runtime
    export LD_LIBRARY_PATH="${pkgs.vulkan-loader}/lib:$LD_LIBRARY_PATH"
    
    # Vulkan Validation Layers (optional, good for debugging)
    export VK_LAYER_PATH="${pkgs.vulkan-validation-layers}/share/vulkan/explicit_layer.d"
    
    # Verify Vulkan availability immediately upon entering shell
    #echo "Checking PyTorch Vulkan support..."
    #python -c "import torch; print(f'Vulkan Available: {torch.is_vulkan_available()}')"
  '';
}