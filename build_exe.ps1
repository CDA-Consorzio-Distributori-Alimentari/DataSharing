param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CliSpecFile = Join-Path $ProjectRoot "datasharing.spec"
$WindowsSpecFile = Join-Path $ProjectRoot "datasharing_windows.spec"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$DeployDir = Join-Path $ProjectRoot "deploy"
$CliExePath = Join-Path $DistDir "datasharing.exe"
$WindowsExePath = Join-Path $DistDir "datasharing_windows.exe"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
    $PythonArgs = @()
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
    $PythonArgs = @()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
    $PythonArgs = @("-3")
} else {
    throw "Python non trovato. Installare Python oppure creare .venv nel progetto."
}

& $PythonCommand @PythonArgs -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller non installato nell'ambiente selezionato. Eseguire: $PythonCommand $($PythonArgs -join ' ') -m pip install pyinstaller"
}

if ($Clean) {
    if (Test-Path $DistDir) {
        Remove-Item $DistDir -Recurse -Force
    }

    if (Test-Path $BuildDir) {
        Remove-Item $BuildDir -Recurse -Force
    }

    if (Test-Path $DeployDir) {
        Remove-Item $DeployDir -Recurse -Force
    }
}

Push-Location $ProjectRoot
try {
    & $PythonCommand @PythonArgs -m PyInstaller --noconfirm $CliSpecFile
    if ($LASTEXITCODE -ne 0) {
        throw "Build PyInstaller CLI terminata con errore. Vedere l'output sopra."
    }

    & $PythonCommand @PythonArgs -m PyInstaller --noconfirm $WindowsSpecFile
    if ($LASTEXITCODE -ne 0) {
        throw "Build PyInstaller Windows terminata con errore. Vedere l'output sopra."
    }
}
finally {
    Pop-Location
}

Copy-Item (Join-Path $ProjectRoot "config.template.json") (Join-Path $DistDir "config.template.json") -Force

if (Test-Path (Join-Path $ProjectRoot "config.json")) {
    Copy-Item (Join-Path $ProjectRoot "config.json") (Join-Path $DistDir "config.json") -Force
}

if (Test-Path $DeployDir) {
    Remove-Item (Join-Path $DeployDir "*") -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $DeployDir | Out-Null
}

if (-not (Test-Path $CliExePath)) {
    throw "Eseguibile CLI non trovato in $CliExePath"
}

if (-not (Test-Path $WindowsExePath)) {
    throw "Eseguibile Windows non trovato in $WindowsExePath"
}

Copy-Item $CliExePath (Join-Path $DeployDir "datasharing.exe") -Force
Copy-Item $WindowsExePath (Join-Path $DeployDir "datasharing_windows.exe") -Force
Copy-Item (Join-Path $ProjectRoot "config.template.json") (Join-Path $DeployDir "config.template.json") -Force
Copy-Item (Join-Path $ProjectRoot "DEPLOY_SERVER.md") (Join-Path $DeployDir "README_DEPLOY.md") -Force

if (Test-Path (Join-Path $ProjectRoot "config.json")) {
    Copy-Item (Join-Path $ProjectRoot "config.json") (Join-Path $DeployDir "config.json") -Force
}

if (Test-Path (Join-Path $ProjectRoot "config.local.json")) {
    Copy-Item (Join-Path $ProjectRoot "config.local.json") (Join-Path $DeployDir "config.local.json") -Force
}