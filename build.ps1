# htmlGENERATOR — PyInstaller build script
# Output: dist/htmlGENERATOR.exe + converter/ + templates/ + README.md
#
# converter/ 和 templates/ 均为外部文件夹，
# 修改后无需重新打包，重启 exe 即生效。
#
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== htmlGENERATOR Build Script ===" -ForegroundColor Cyan

# 1. 确保 PyInstaller 已安装
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# 2. 确保依赖已安装
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt 2>&1 | Out-Null
pip install tkinterdnd2 2>&1 | Out-Null

# 3. 清理旧构建
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path htmlGENERATOR.spec) { Remove-Item htmlGENERATOR.spec }

# 4. PyInstaller 打包
#    converter/ 和 templates/ 不捆绑 —— 外部文件夹支持热修改
Write-Host "Building..." -ForegroundColor Yellow
pyinstaller `
    --name "htmlGENERATOR" `
    --onefile `
    --windowed `
    --clean `
    --noconfirm `
    --hidden-import "lxml.etree" `
    --hidden-import "docx" `
    --hidden-import "fitz" `
    --hidden-import "jinja2" `
    --hidden-import "jinja2.ext" `
    --hidden-import "PIL" `
    --hidden-import "tkinterdnd2" `
    gui_app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# 5. 复制外部可编辑文件到 dist
Write-Host "Copying converter/ templates/ README.md ..." -ForegroundColor Yellow
Copy-Item -Recurse -Force converter dist\
Copy-Item -Recurse -Force templates dist\
Copy-Item README.md dist\

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Green
Write-Host "  dist/htmlGENERATOR.exe   (standalone, no deps)"
Write-Host "  dist/converter/           (editable Python, no rebuild)"
Write-Host "  dist/templates/           (editable HTML/CSS/XSL, no rebuild)"
Write-Host "  dist/README.md"
Write-Host ""
$size = (Get-Item dist/htmlGENERATOR.exe).Length / 1MB
Write-Host ("  exe size: {0:F0} MB" -f $size)
