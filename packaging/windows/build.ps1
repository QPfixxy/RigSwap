# Build the Windows installer: PyInstaller, then Inno Setup.
#
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 [-Arch x64|arm64]
#
# Needs: Python with RigSwap and PyInstaller installed (pip install -e ".[build]") and
# Inno Setup 6 (winget install JRSoftware.InnoSetup). Output: dist\RigSwap-<version>-windows-<arch>-setup.exe
param([ValidateSet("x64", "arm64")] [string]$Arch = "x64")
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $root

$version = python -c "import rigswap; print(rigswap.__version__)"
# Windows wants four numbers: 2.0.0a1 -> 2.0.0.1
$numeric = python -c "import re, rigswap; n = re.findall(r'\d+', rigswap.__version__) + ['0'] * 4; print('.'.join(n[:4]))"
Write-Host "Building RigSwap $version ($Arch)"

python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\pyinstaller\rigswap.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 not found (winget install JRSoftware.InnoSetup)" }
$allowed = if ($Arch -eq "arm64") { "arm64" } else { "x64compatible" }
& $iscc "/DAppVersion=$version" "/DNumericVersion=$numeric" "/DArch=$Arch" "/DArchAllowed=$allowed" packaging\windows\rigswap.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Get-ChildItem dist\*.exe | ForEach-Object { Write-Host "Built $($_.FullName)" }
