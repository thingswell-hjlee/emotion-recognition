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

$ErrorActionPreference = "Stop"

# ──────────────────────────────────────
# Configuration
# ──────────────────────────────────────
$Version = "0.1.0"
$ReleaseName = "emotion-recognition-beta-win64-v$Version-thingswell"
$ZipFileName = "$ReleaseName.zip"
$ProjectRoot = $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Thingswell Inc." -ForegroundColor Cyan
Write-Host " Multimodal Emotion Recognition & Korean STT Monitor" -ForegroundColor Cyan
Write-Host " Beta Test Release v$Version" -ForegroundColor Cyan
Write-Host " Building release package..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ──────────────────────────────────────
# Create staging directory
# ──────────────────────────────────────
$StagingDir = Join-Path $ProjectRoot "dist\$ReleaseName"

if (Test-Path $StagingDir) {
    Remove-Item -Recurse -Force $StagingDir
}
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\ui" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\modules" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\utils" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\models" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\release" -Force | Out-Null
New-Item -ItemType Directory -Path "$StagingDir\release\scripts" -Force | Out-Null

Write-Host "[INFO] Staging directory created: $StagingDir"

# ──────────────────────────────────────
# Copy required files
# ──────────────────────────────────────
Write-Host "[INFO] Copying files..."

# Root-level required files
$RootFiles = @(
    "README.md",
    "setup-guide.md",
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
    "requirements-stt.txt"
)

foreach ($file in $RootFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination $StagingDir
        Write-Host "  [OK] $file"
    } else {
        Write-Host "  [WARN] $file not found, skipping." -ForegroundColor Yellow
    }
}

# UI files
Write-Host "  Copying ui/..."
Copy-Item "$ProjectRoot\ui\*" -Destination "$StagingDir\ui\" -Recurse

# Modules
Write-Host "  Copying modules/..."
Copy-Item "$ProjectRoot\modules\*" -Destination "$StagingDir\modules\" -Recurse

# Utils
Write-Host "  Copying utils/..."
Copy-Item "$ProjectRoot\utils\*" -Destination "$StagingDir\utils\" -Recurse

# Models
Write-Host "  Copying models/..."
Copy-Item "$ProjectRoot\models\*" -Destination "$StagingDir\models\" -Recurse

# Release documents
$ReleaseFiles = @(
    "release\README_TESTER.md",
    "release\TEST_CHECKLIST.md",
    "release\TROUBLESHOOTING.md",
    "release\RELEASE_NOTES.md"
)

foreach ($file in $ReleaseFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination "$StagingDir\release\"
        Write-Host "  [OK] $file"
    } else {
        Write-Host "  [WARN] $file not found, skipping." -ForegroundColor Yellow
    }
}

# Release scripts
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

foreach ($file in $ScriptFiles) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item $src -Destination "$StagingDir\release\scripts\"
        Write-Host "  [OK] $file"
    } else {
        Write-Host "  [WARN] $file not found, skipping." -ForegroundColor Yellow
    }
}

# ──────────────────────────────────────
# Create ZIP
# ──────────────────────────────────────
Write-Host ""
Write-Host "[INFO] Creating ZIP archive..."

$ZipPath = Join-Path $ProjectRoot "dist\$ZipFileName"

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

Compress-Archive -Path $StagingDir -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " [DONE] Release package created:" -ForegroundColor Green
Write-Host " $ZipPath" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host " ZIP filename: $ZipFileName" -ForegroundColor Green
Write-Host " Folder name:  $ReleaseName" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host " Thingswell Inc." -ForegroundColor DarkGray
Write-Host " Copyright (c) 2026 Thingswell Inc. All rights reserved." -ForegroundColor DarkGray
