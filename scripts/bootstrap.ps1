# scripts/bootstrap.ps1 -- one-command installer for ai-scientist plugin (v2.1+).
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/bootstrap.ps1 | iex
#
# Auto-detects Claude Code / Codex CLI / Gemini CLI in ~/.{claude,codex,gemini}/
# and registers the plugin with each one. Idempotent: re-runs are safe.
#
# Pure ASCII so non-UTF-8 PowerShell sessions parse it correctly.

$ErrorActionPreference = "Continue"

$RepoUrl   = "https://github.com/danilkotelnikov/ai-scientist-plugin.git"
$Branch    = "master"
$RepoDir   = "$env:USERPROFILE\.ai-scientist\repo"
$AiHome    = "$env:USERPROFILE\.ai-scientist"
$PalaceDir = "$AiHome\palace"

function Step([string]$msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok([string]$msg)   { Write-Host "  [OK]   $msg" -ForegroundColor Green }
function Note([string]$msg) { Write-Host "  [NOTE] $msg" -ForegroundColor Yellow }
function Fail([string]$msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

function Invoke-Native {
    param([Parameter(Mandatory)][scriptblock]$Script,
          [string]$Description = "command",
          [switch]$IgnoreExitCode)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Script
        $code = $LASTEXITCODE
        if (-not $IgnoreExitCode -and $code -ne 0) {
            throw "$Description failed (exit $code)"
        }
        return $code
    } finally { $ErrorActionPreference = $prev }
}

Write-Host ""
Write-Host "AI-Scientist Plugin -- one-command bootstrap" -ForegroundColor Magenta
Write-Host ""

# 1. Probe prerequisites
Step "Probing prerequisites"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Fail "Python 3.11+ not found in PATH. Install: winget install --id Python.Python.3.11"
    exit 1
}
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Fail "git not found. Install: winget install --id Git.Git"
    exit 1
}
Ok "python: $((& python --version 2>&1) -join ' ')"
Ok "git:    $((& git --version 2>&1) -join ' ')"

# 2. Clone or update the canonical repo
Step "Syncing canonical repo at $RepoDir"
New-Item -ItemType Directory -Force -Path $AiHome | Out-Null
if (Test-Path "$RepoDir\.git") {
    Push-Location $RepoDir
    Invoke-Native -IgnoreExitCode -Description "git stash" -Script {
        git stash push --include-untracked -m "auto-stash by bootstrap.ps1 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" *>&1 | Out-Null
    }
    Invoke-Native -IgnoreExitCode -Description "git fetch" -Script {
        git fetch --quiet origin $Branch
    }
    Invoke-Native -IgnoreExitCode -Description "git reset" -Script {
        git reset --hard "origin/$Branch" --quiet
    }
    Pop-Location
    Ok "Updated existing clone (any local changes saved as a stash)"
} else {
    Invoke-Native -Description "git clone" -Script {
        git clone --quiet --branch $Branch $RepoUrl $RepoDir
    }
    Ok "Cloned fresh"
}

$Plug = "$RepoDir\plugins\ai-scientist"

# 3. Install Python dependencies (idempotent, --user)
Step "Installing Python dependencies (user-site)"
Invoke-Native -IgnoreExitCode -Description "pip install requirements" -Script {
    python -m pip install --user --quiet -r "$Plug\mcp\requirements.txt" 2>&1 | Out-Null
}
Ok "MCP requirements present"

Invoke-Native -IgnoreExitCode -Description "pip install mempalace" -Script {
    python -m pip install --user --quiet mempalace 2>&1 | Out-Null
}
Ok "mempalace package present"

if (-not (Test-Path $PalaceDir)) {
    New-Item -ItemType Directory -Path $PalaceDir -Force | Out-Null
}
$mempalaceCmd = Get-Command mempalace -ErrorAction SilentlyContinue
if ($mempalaceCmd) {
    Invoke-Native -IgnoreExitCode -Description "mempalace init" -Script {
        mempalace init "$PalaceDir" *>&1 | Out-Null
    }
    Ok "MemPalace initialized at $PalaceDir"
} else {
    Note "mempalace CLI not on PATH yet; reopen the shell or set %PATH%"
}

# 4. Codex CLI -- auto-merge config + create junctions
if (Test-Path "$env:USERPROFILE\.codex") {
    Write-Host ""
    Step "Codex CLI detected -- registering plugin"

    # 4a. Junction the codex clone (so .codex/INSTALL.md and existing tooling
    #     keep working at the well-known path).
    $codexClone = "$env:USERPROFILE\.codex\ai-scientist-plugin"
    if (-not (Test-Path $codexClone)) {
        cmd /c mklink /J "$codexClone" "$RepoDir" 2>&1 | Out-Null
        Ok "Junctioned ~/.codex/ai-scientist-plugin -> $RepoDir"
    } else {
        Ok "~/.codex/ai-scientist-plugin already present"
    }

    # 4b. Junction skill + agents into ~/.agents/
    New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"  | Out-Null
    New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\agents"  | Out-Null
    foreach ($pair in @(
        @("$env:USERPROFILE\.agents\skills\ai-scientist", "$Plug\skills\ai-scientist"),
        @("$env:USERPROFILE\.agents\agents\ai-scientist", "$Plug\agents")
    )) {
        $linkPath, $target = $pair
        if (Test-Path $linkPath) {
            cmd /c rmdir "$linkPath" 2>&1 | Out-Null
        }
        cmd /c mklink /J "$linkPath" "$target" 2>&1 | Out-Null
    }
    Ok "Junctioned skill + agents into ~/.agents/"

    # 4c. Auto-merge config.toml (idempotent; never duplicates)
    $configToml = "$env:USERPROFILE\.codex\config.toml"
    Invoke-Native -Description "merge codex config.toml" -Script {
        python "$RepoDir\scripts\_merge_codex_config.py" `
            --user "$configToml" `
            --example "$Plug\codex-config.toml.example" `
            --quiet
    }
    Ok "config.toml merged (sentinel-bracketed; idempotent)"
} else {
    Note "Codex CLI not detected at ~/.codex/ -- skipping Codex registration"
}

# 5. Gemini CLI -- run extension install
if (Test-Path "$env:USERPROFILE\.gemini") {
    Write-Host ""
    Step "Gemini CLI detected -- installing extension"
    $gemini = Get-Command gemini -ErrorAction SilentlyContinue
    if ($gemini) {
        Invoke-Native -IgnoreExitCode -Description "gemini extensions install" -Script {
            gemini extensions install $RepoUrl 2>&1 | Out-Null
        }
        Ok "Gemini extension installed"
    } else {
        Note "gemini CLI not on PATH; install Gemini CLI then re-run this bootstrap"
    }
} else {
    Note "Gemini CLI not detected at ~/.gemini/ -- skipping Gemini registration"
}

# 6. Claude Code -- print the two slash commands
if (Test-Path "$env:USERPROFILE\.claude") {
    Write-Host ""
    Step "Claude Code detected"
    Note "Open a Claude Code session and paste these two slash commands:"
    Write-Host "      /plugin marketplace add danilkotelnikov/ai-scientist-plugin" -ForegroundColor White
    Write-Host "      /plugin install ai-scientist@ai-scientist-plugin"             -ForegroundColor White
    Note "These cannot be issued from outside the agent (slash commands are session-only)."
} else {
    Note "Claude Code not detected at ~/.claude/ -- skipping Claude registration"
}

# 7. MCP self-test
Write-Host ""
Step "Running MCP self-test"
$prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$selftest = (& python "$Plug\mcp\server.py" --selftest 2>&1) -join "`n"
$selftestCode = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($selftestCode -eq 0 -and $selftest -match "selftest: OK") {
    Ok ($selftest -replace "`n", "; ")
} else {
    Note "self-test exit $selftestCode; output: $selftest"
}

# 8. Probe required env var
Write-Host ""
Step "Environment variables"
if (-not $env:OPENALEX_EMAIL) {
    Note "OPENALEX_EMAIL is not set. Set it once via:"
    Write-Host "      [Environment]::SetEnvironmentVariable('OPENALEX_EMAIL', 'you@example.com', 'User')" -ForegroundColor White
    Note "(close + reopen the shell after setting; required since 2026-02-13 for OpenAlex)"
} else {
    Ok "OPENALEX_EMAIL = $env:OPENALEX_EMAIL"
}
foreach ($v in @("SEMANTIC_SCHOLAR_KEY", "ANNAS_BASE_URL", "ANNAS_DOWNLOAD_PATH", "ANNAS_SECRET_KEY")) {
    $val = [Environment]::GetEnvironmentVariable($v, "Process")
    if ($val) { Ok "$v = (set)" } else { Note "$v not set (optional)" }
}

# 9. Summary
Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "  - canonical repo: $RepoDir"
Write-Host "  - update later:   iwr -useb https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/update.ps1 | iex"
Write-Host ""
