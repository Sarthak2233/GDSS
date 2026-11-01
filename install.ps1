# ==============================================================================
# GDSS Standalone Binary Universal Installer (Windows PowerShell)
# https://github.com/sarthak2233/gdss-radar
# ==============================================================================
[CmdletBinding()]
param (
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

Write-Host "🛰️  GDSS Standalone Windows Installer" -ForegroundColor Cyan
Write-Host "--------------------------------------------------"

# 1. Detect Architecture
$Arch = $env:PROCESSOR_ARCHITECTURE
if ($Arch -ne "AMD64") {
    Write-Warning "Detected architecture '$Arch'. GDSS official Windows binary is compiled for x86_64 (AMD64)."
}
$Target = "windows-amd64"

# 2. Determine Version
$Repo = "sarthak2233/gdss-radar"
if ([string]::IsNullOrWhiteSpace($Version)) {
    Write-Host "Resolving latest GDSS release..."
    try {
        $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ "User-Agent" = "GDSS-Installer" }
        $Version = $Release.tag_name
    } catch {
        $Version = "v1"
    }
}
Write-Host "Target version: $Version" -ForegroundColor Yellow

$ArchiveName = "gdss-$Version-$Target.zip"
$DownloadUrl = "https://github.com/$Repo/releases/download/$Version/$ArchiveName"

# 3. Create Temp Directory and Download
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    $ZipPath = Join-Path $TempDir $ArchiveName
    Write-Host "Downloading $ArchiveName..."
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing

    # 4. Extract
    Write-Host "Extracting binary..."
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

    $ExtractedExe = Join-Path $TempDir "gdss.exe"
    if (-not (Test-Path $ExtractedExe)) {
        throw "Extracted archive did not contain 'gdss.exe'."
    }

    # 5. Destination Directory
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\gdss"
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    $DestExe = Join-Path $InstallDir "gdss.exe"

    Copy-Item -Path $ExtractedExe -Destination $DestExe -Force
    Write-Host "✓ Installed gdss.exe to $DestExe" -ForegroundColor Green

    # 6. Update User PATH
    $UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
    if ($UserPath -notlike "*$InstallDir*") {
        Write-Host "Adding $InstallDir to User PATH..."
        $NewPath = "$UserPath;$InstallDir"
        [Environment]::SetEnvironmentVariable("Path", $NewPath, [EnvironmentVariableTarget]::User)
        $env:Path = "$env:Path;$InstallDir"
        Write-Host "✓ PATH updated. (Restart open terminals to refresh)" -ForegroundColor Green
    }

    Write-Host "`n✓ GDSS successfully installed!" -ForegroundColor Green
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. Check status:       gdss status"
    Write-Host "  2. Compute radar:      gdss tensor"
    Write-Host "  3. Claude Code MCP:    claude mcp add gdss -- gdss mcp"
    Write-Host "  4. Cursor IDE MCP:     Add to %USERPROFILE%\.cursor\mcp.json:"
    Write-Host @"
     {
       "mcpServers": {
         "gdss": { "command": "gdss", "args": ["mcp"] }
       }
     }
"@
}
finally {
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
