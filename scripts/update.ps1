# scripts/update.ps1 -- one-command updater for ai-scientist plugin (v2.1+).
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/update.ps1 | iex
#
# Re-runs bootstrap.ps1 (the bootstrap is itself idempotent and handles
# clone-or-pull, dep refresh, config re-merge, and self-test).

$ErrorActionPreference = "Continue"
Write-Host ""
Write-Host "AI-Scientist Plugin -- update via bootstrap" -ForegroundColor Magenta
$bootstrap = "https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/bootstrap.ps1"
$src = (Invoke-WebRequest -UseBasicParsing -Uri $bootstrap).Content
Invoke-Expression $src
