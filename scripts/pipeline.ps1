# docx → HTML 完整流水线
#   pandoc:     .docx → .md + media/
#   SUMMARY.md  自动生成
#   build_site: .md → 静态 HTML 站点 (Python, 无 Node.js 依赖)
#
# 用法: .\scripts\pipeline.ps1

$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot ".."
$inputDir   = Join-Path $root "input"
$contentDir = Join-Path $root "content"
$outputDir  = Join-Path $root "output"

# 查找 pandoc（优先项目内置，其次系统 PATH）
$pandoc = $null
$bundledPandoc = Join-Path $root "tools\pandoc\pandoc.exe"
if (Test-Path $bundledPandoc) {
    $pandoc = $bundledPandoc
} else {
    $pandoc = (Get-Command pandoc -ErrorAction SilentlyContinue).Source
}
if (-not $pandoc) {
    Write-Host "错误: 未找到 pandoc。请放入 tools/pandoc/pandoc.exe 或安装到系统 PATH。" -ForegroundColor Red
    exit 1
}
Write-Host "pandoc: $pandoc"

# ═══════════════════════════════════════════════════════════════
# 阶段 1 — pandoc: docx → md
# ═══════════════════════════════════════════════════════════════
Write-Host "`n=== [1/3] pandoc: docx → md ===" -ForegroundColor Cyan

$docxFiles = Get-ChildItem $inputDir -Filter "*.docx" -ErrorAction SilentlyContinue
if (-not $docxFiles) {
    Write-Host "  未在 input/ 找到 .docx 文件，跳过。"
} else {
    New-Item -ItemType Directory -Force $contentDir | Out-Null
    foreach ($f in $docxFiles) {
        $outName = $f.BaseName -replace '\s+', '-' -replace '[^\w\-]', ''
        $mdPath  = Join-Path $contentDir "$outName.md"
        Write-Host "  $($f.Name) → content/$outName.md"
        & $pandoc $f.FullName -o $mdPath `
            --from docx `
            --to gfm `
            --extract-media (Join-Path $contentDir "media") `
            --wrap=none `
            --markdown-headings=atx
    }
}

# ═══════════════════════════════════════════════════════════════
# 阶段 2 — 生成 SUMMARY.md
# ═══════════════════════════════════════════════════════════════
Write-Host "`n=== [2/3] 生成 SUMMARY.md ===" -ForegroundColor Cyan

$mdFiles = Get-ChildItem $contentDir -Filter "*.md" |
    Where-Object { $_.Name -ne "README.md" -and $_.Name -ne "SUMMARY.md" } |
    Sort-Object Name

$summary = @("# 目录`n")
foreach ($f in $mdFiles) {
    $firstLine = Get-Content $f.FullName -First 1 -ErrorAction SilentlyContinue
    $title = $f.BaseName
    if ($firstLine -match '^#\s+(.+)') {
        $title = $Matches[1]
    }
    $summary += "- [$title]($($f.Name))"
}

$summaryPath = Join-Path $contentDir "SUMMARY.md"
$summary -join "`n" | Set-Content $summaryPath -Encoding UTF8
Write-Host "  已生成 SUMMARY.md ($($mdFiles.Count) 个条目)"

# ═══════════════════════════════════════════════════════════════
# 阶段 3 — Python 静态站点生成
# ═══════════════════════════════════════════════════════════════
Write-Host "`n=== [3/3] build_site (Python) ===" -ForegroundColor Cyan

Copy-Item (Join-Path $root "book.json") (Join-Path $contentDir "book.json") -Force

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = "python" }

& $python (Join-Path $PSScriptRoot "build_site.py") $contentDir $outputDir
Write-Host "  输出: $outputDir" -ForegroundColor Green

Write-Host "`n完成。打开: $outputDir\index.html" -ForegroundColor Green
