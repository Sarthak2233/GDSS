# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for GDSS standalone binary distribution.
Builds a single-file executable bundling CLI, MCP server, Tree-sitter parsers,
and all core dependencies across Linux, macOS, and Windows.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Base directory of the repository
repo_root = os.path.abspath(os.path.join(SPECPATH, '..', '..'))
entry_script = os.path.join(repo_root, 'gdss', 'cli', 'main.py')

datas = []
binaries = []
hiddenimports = [
    'git',
    'gitdb',
    'smmap',
    'rich',
    'rich.logging',
    'rich.table',
    'rich.tree',
    'rich.progress',
    'typer',
    'typer.core',
    'yaml',
    'httpx',
    'httpcore',
    'watchdog',
    'watchdog.observers',
    'pydantic',
    'pydantic_core',
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.protocols',
    'uvicorn.lifespan',
    'networkx',
    'numpy',
]

# Explicitly collect all Tree-sitter language grammars and runtime data
tree_sitter_packages = [
    'tree_sitter',
    'tree_sitter_python',
    'tree_sitter_javascript',
    'tree_sitter_typescript',
    'tree_sitter_go',
    'tree_sitter_rust',
    'tree_sitter_java',
    'tree_sitter_c',
    'tree_sitter_cpp',
    'uvicorn',
    'fastapi',
    'networkx',
    'pydantic',
]

for pkg in tree_sitter_packages:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:
        print(f"Warning: Failed to collect {pkg}: {exc}", file=sys.stderr)

a = Analysis(
    [entry_script],
    pathex=[repo_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'notebook',
        'PIL',
        'torch',
        'tensorflow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gdss',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

