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
$GuidePath = Join-Path $ProjectRoot "GUIDA_UTENTE_DATASHARING.md"
$ConfigPath = Join-Path $ProjectRoot "config.json"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$DeployFiles = @(
    "datasharing.exe",
    "datasharing_windows.exe",
    "config.json",
    "GUIDA_UTENTE_DATASHARING.md"
)

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

        if (Test-Path $stdoutPath) {
            Get-Content $stdoutPath | ForEach-Object { Write-Host $_ }
        }

        if (Test-Path $stderrPath) {
            Get-Content $stderrPath | ForEach-Object { Write-Host $_ }
        }

        return $process.ExitCode
    }
    finally {
        if (Test-Path $stdoutPath) {
            Remove-Item $stdoutPath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $stderrPath) {
            Remove-Item $stderrPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Clear-DirectoryContents {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return
    }

    Get-ChildItem -Path $Path -Force | ForEach-Object {
        if ($DeployFiles -contains $_.Name) {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
        }
    }
}

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

$pyInstallerVersionExitCode = Invoke-NativeCommand -FilePath $PythonCommand -Arguments (@($PythonArgs) + @("-m", "PyInstaller", "--version"))
if ($pyInstallerVersionExitCode -ne 0) {
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
        try {
            Remove-Item $DeployDir -Recurse -Force -ErrorAction Stop
        }
        catch {
            throw "Impossibile pulire la cartella deploy. Chiudere eventuali exe avviati da '$DeployDir' e riprovare. Dettaglio: $($_.Exception.Message)"
        }
    }
}

Push-Location $ProjectRoot
try {
    $cliBuildExitCode = Invoke-NativeCommand -FilePath $PythonCommand -Arguments (@($PythonArgs) + @("-m", "PyInstaller", "--noconfirm", $CliSpecFile))
    if ($cliBuildExitCode -ne 0) {
        throw "Build PyInstaller CLI terminata con errore. Vedere l'output sopra."
    }

    $windowsBuildExitCode = Invoke-NativeCommand -FilePath $PythonCommand -Arguments (@($PythonArgs) + @("-m", "PyInstaller", "--noconfirm", $WindowsSpecFile))
    if ($windowsBuildExitCode -ne 0) {
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
    try {
        Clear-DirectoryContents -Path $DeployDir
    }
    catch {
        throw "Impossibile aggiornare la cartella deploy. Chiudere eventuali exe aperti da '$DeployDir' e riprovare. Dettaglio: $($_.Exception.Message)"
    }
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

if (Test-Path $ConfigPath) {
    Copy-Item $ConfigPath (Join-Path $DeployDir "config.json") -Force
}

if (Test-Path $GuidePath) {
    Copy-Item $GuidePath (Join-Path $DeployDir "GUIDA_UTENTE_DATASHARING.md") -Force
}

Write-Host "Pacchetto deploy pronto in: $DeployDir"