# htmlGENERATOR v2 — 驱动脚本
# 用法: .\build.ps1
#
# 流水线: pandoc (docx→md) → SUMMARY.md → 静态 HTML 站点
# 前置: pandoc 在 PATH 或 tools/pandoc/pandoc.exe

$ErrorActionPreference = "Stop"
$root = Split-Path $MyInvocation.MyCommand.Path -Parent

& (Join-Path $root "scripts" "pipeline.ps1")
