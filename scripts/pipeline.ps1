# docx → HTML 完整流水线
#   pandoc: .docx → .md + media/
#   SUMMARY.md 自动生成
#   honkit:   .md → 静态 HTML 站点
#
# 前提: pandoc (PATH), node/npm, honkit (npm install -g honkit)
# 用法: .\scripts\pipeline.ps1

$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot ".."
$inputDir  = Join-Path $root "input"
$contentDir = Join-Path $root "content"
$outputDir  = Join-Path $root "output"

# ═══════════════════════════════════════════════════════════════
# 阶段 1 — pandoc: docx → md
# ═══════════════════════════════════════════════════════════════
Write-Host "=== [1/3] pandoc: docx → md ===" -ForegroundColor Cyan

$docxFiles = Get-ChildItem $inputDir -Filter "*.docx" -ErrorAction SilentlyContinue
if (-not $docxFiles) {
    Write-Host "  未在 input/ 找到 .docx 文件，跳过。"
} else {
    New-Item -ItemType Directory -Force $contentDir | Out-Null
    foreach ($f in $docxFiles) {
        $outName = $f.BaseName -replace '\s+', '-' -replace '[^\w\-]', ''
        $mdPath  = Join-Path $contentDir "$outName.md"
        Write-Host "  $($f.Name) → content/$outName.md"
        pandoc $f.FullName -o $mdPath `
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

# 收集所有 .md 文件，按文件名排序
$mdFiles = Get-ChildItem $contentDir -Filter "*.md" |
    Where-Object { $_.Name -ne "README.md" -and $_.Name -ne "SUMMARY.md" } |
    Sort-Object Name

# 生成 SUMMARY.md
$summary = @("# 目录`n")
foreach ($f in $mdFiles) {
    # 尝试从文件第一行提取 H1 标题
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
# 阶段 3 — honkit 构建
# ═══════════════════════════════════════════════════════════════
Write-Host "`n=== [3/3] honkit build ===" -ForegroundColor Cyan

# 将 book.json 同步到 content/
Copy-Item (Join-Path $root "book.json") (Join-Path $contentDir "book.json") -Force

Push-Location $contentDir
try {
    $null = honkit build . $outputDir 2>&1
    Write-Host "  输出: $outputDir" -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host "`n完成。" -ForegroundColor Green
