# ============================================
# Thingswell Inc.
# Multimodal Emotion Recognition & Korean STT Monitor
# Beta Test Release v0.1.0
# Copyright (c) 2026 Thingswell Inc.
# Contact: hjlee@thingswell.co.kr
# ============================================
#
# Release Package Build Script
# Creates the distribution ZIP file for Windows beta testing.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File make_release_zip.ps1
#

$ErrorActionPreference = "Stop"

# ──────────────────────────────────────
# Configuration
# ──────────────────────────────────────
$Version = "0.1.0"
$ReleaseName = "emotion-recognition-beta-win64-v$Version-thingswell"
$ZipFileName = "$ReleaseName.zip"
$ProjectRoot = $PSScriptRoot
$DistDir = Join-Path $ProjectRoot "dist"
$StagingDir = Join-Path $DistDir $ReleaseName
$ZipPath = Join-Path $DistDir $ZipFileName

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Thingswell Inc." -ForegroundColor Cyan
Write-Host " Multimodal Emotion Recognition & Korean STT Monitor" -ForegroundColor Cyan
Write-Host " Beta Test Release v$Version" -ForegroundColor Cyan
Write-Host " Building release package..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ──────────────────────────────────────
# Exclusion patterns
# ──────────────────────────────────────
$ExcludeDirs = @(
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "logs",
    "test_report",
    "dist",
    "node_modules",
    ".mypy_cache"
)

$ExcludeExtensions = @(
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    "*.tmp",
    "*.log"
)

Write-Host "[INFO] Excluded directories: $($ExcludeDirs -join ', ')" -ForegroundColor DarkGray
Write-Host "[INFO] Excluded extensions: $($ExcludeExtensions -join ', ')" -ForegroundColor DarkGray
Write-Host ""

# ──────────────────────────────────────
# Clean previous build
# ──────────────────────────────────────
if (Test-Path $StagingDir) {
    Write-Host "[INFO] Cleaning previous staging directory..."
    Remove-Item -Recurse -Force $StagingDir
}
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

# Create dist directory
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

# ──────────────────────────────────────
# Create staging directory structure
# ──────────────────────────────────────
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\ui" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\modules" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\utils" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\models" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\release" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\release\scripts" -Force | Out-Null

Write-Host "[INFO] Staging directory: $StagingDir"
Write-Host ""

# ──────────────────────────────────────
# Copy root-level files (required)
# ──────────────────────────────────────
Write-Host "[INFO] Copying root-level files..."

$RootFiles = @(
    "README.md",
    "setup-guide.md",
    "privacy-notice.md",
    "NOTICE.md",
    "LICENSE-THINGSWELL.md",
    "version.py",
    "config.py",
    "controller.py",
    "main.py",
    "performance_profiles.py",
    "requirements.txt",
    "requirements-minimal.txt",
    "requirements-face.txt",
    "requirements-voice.txt",
    "requirements-stt.txt",
    "requirements-stt-openai-optional.txt"
)

$copiedRoot = 0
foreach ($file in $RootFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination $StagingDir
        Write-Host "  [OK] $file" -ForegroundColor Green
        $copiedRoot++
    } else {
        Write-Host "  [WARN] $file not found, skipping." -ForegroundColor Yellow
    }
}
Write-Host "  ($copiedRoot/$($RootFiles.Count) root files copied)"
Write-Host ""

# ──────────────────────────────────────
# Copy directories (excluding __pycache__)
# ──────────────────────────────────────
$DirectoriesToCopy = @(
    @{ Name = "ui"; Dest = "ui" },
    @{ Name = "modules"; Dest = "modules" },
    @{ Name = "utils"; Dest = "utils" },
    @{ Name = "models"; Dest = "models" }
)

$copiedDirs = 0
foreach ($dir in $DirectoriesToCopy) {
    $srcDir = Join-Path $ProjectRoot $dir.Name
    $destDir = Join-Path $StagingDir $dir.Dest
    if (Test-Path $srcDir) {
        Write-Host "[INFO] Copying $($dir.Name)/..."
        # Copy excluding __pycache__
        Get-ChildItem -Path $srcDir -Recurse |
            Where-Object { $_.FullName -notmatch "__pycache__" -and $_.FullName -notmatch "\.pyc$" } |
            ForEach-Object {
                $relativePath = $_.FullName.Substring($srcDir.Length)
                $targetPath = Join-Path $destDir $relativePath
                if ($_.PSIsContainer) {
                    New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
                } else {
                    $targetDir = Split-Path $targetPath -Parent
                    if (-not (Test-Path $targetDir)) {
                        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                    }
                    Copy-Item $_.FullName -Destination $targetPath
                }
            }
        $fileCount = (Get-ChildItem -Path $destDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "  [OK] $($dir.Name)/ ($fileCount files)" -ForegroundColor Green
        $copiedDirs++
    } else {
        Write-Host "  [SKIP] $($dir.Name)/ not found" -ForegroundColor Yellow
    }
}
Write-Host ""

# ──────────────────────────────────────
# Copy release documents
# ──────────────────────────────────────
Write-Host "[INFO] Copying release documents..."

$ReleaseFiles = @(
    "release\README_TESTER.md",
    "release\TEST_CHECKLIST.md",
    "release\TROUBLESHOOTING.md",
    "release\RELEASE_NOTES.md"
)

$copiedRelease = 0
foreach ($file in $ReleaseFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination "$StagingDir\release\"
        Write-Host "  [OK] $file" -ForegroundColor Green
        $copiedRelease++
    } else {
        Write-Host "  [WARN] $file not found" -ForegroundColor Yellow
    }
}
Write-Host ""

# ──────────────────────────────────────
# Copy release scripts
# ──────────────────────────────────────
Write-Host "[INFO] Copying release scripts..."

$ScriptFiles = @(
    "release\scripts\install_all.bat",
    "release\scripts\install_minimal.bat",
    "release\scripts\install_face.bat",
    "release\scripts\install_voice.bat",
    "release\scripts\install_stt.bat",
    "release\scripts\run_app.bat",
    "release\scripts\health_check.bat",
    "release\scripts\collect_logs.bat"
)

$copiedScripts = 0
foreach ($file in $ScriptFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination "$StagingDir\release\scripts\"
        Write-Host "  [OK] $file" -ForegroundColor Green
        $copiedScripts++
    } else {
        Write-Host "  [WARN] $file not found" -ForegroundColor Yellow
    }
}
Write-Host ""

# ──────────────────────────────────────
# Create ZIP archive
# ──────────────────────────────────────
Write-Host "[INFO] Creating ZIP archive..."
Write-Host "  Source: $StagingDir"
Write-Host "  Target: $ZipPath"

Compress-Archive -Path "$StagingDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

$zipSize = (Get-Item $ZipPath).Length
$zipSizeMB = [math]::Round($zipSize / 1MB, 2)

# ──────────────────────────────────────
# Count total files in package
# ──────────────────────────────────────
$totalFiles = (Get-ChildItem -Path $StagingDir -Recurse -File | Measure-Object).Count

# ──────────────────────────────────────
# Summary output
# ──────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " BUILD COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host " ZIP File:     $ZipFileName" -ForegroundColor White
Write-Host " ZIP Path:     $ZipPath" -ForegroundColor White
Write-Host " ZIP Size:     $zipSizeMB MB" -ForegroundColor White
Write-Host " Total Files:  $totalFiles" -ForegroundColor White
Write-Host " Folder Name:  $ReleaseName" -ForegroundColor White
Write-Host ""
Write-Host " Included:" -ForegroundColor Cyan
Write-Host "   Root files:     $copiedRoot" -ForegroundColor White
Write-Host "   Directories:    $copiedDirs (ui, modules, utils, models)" -ForegroundColor White
Write-Host "   Release docs:   $copiedRelease" -ForegroundColor White
Write-Host "   BAT scripts:    $copiedScripts" -ForegroundColor White
Write-Host ""
Write-Host " Excluded:" -ForegroundColor Yellow
Write-Host "   .git, .venv, __pycache__, .pytest_cache" -ForegroundColor DarkGray
Write-Host "   logs, test_report, dist, *.pyc, *.log" -ForegroundColor DarkGray
Write-Host ""
Write-Host " Tester Execution Order:" -ForegroundColor Cyan
Write-Host "   1. Unzip $ZipFileName" -ForegroundColor White
Write-Host "   2. cd $ReleaseName\release\scripts" -ForegroundColor White
Write-Host "   3. install_all.bat" -ForegroundColor White
Write-Host "   4. health_check.bat" -ForegroundColor White
Write-Host "   5. run_app.bat" -ForegroundColor White
Write-Host "   6. Open http://localhost:8501" -ForegroundColor White
Write-Host "   7. Test: minimal -> face -> voice -> full" -ForegroundColor White
Write-Host "   8. collect_logs.bat" -ForegroundColor White
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Thingswell Inc." -ForegroundColor DarkGray
Write-Host " Copyright (c) 2026 Thingswell Inc." -ForegroundColor DarkGray
Write-Host " All rights reserved." -ForegroundColor DarkGray
Write-Host "============================================" -ForegroundColor Green
