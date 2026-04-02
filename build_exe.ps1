param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VersionFilePath = Join-Path $ProjectRoot "VERSION"
$CliSpecFile = Join-Path $ProjectRoot "datasharing.spec"
$WindowsSpecFile = Join-Path $ProjectRoot "datasharing_windows.spec"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$DeployDir = Join-Path $ProjectRoot "deploy"
$ReleaseDir = "\\cdabackup\DataSharing\release"
$CliExePath = Join-Path $DistDir "datasharing.exe"
$WindowsExePath = Join-Path $DistDir "datasharing_windows.exe"
$GuidePath = Join-Path $ProjectRoot "GUIDA_UTENTE_DATASHARING.md"
$ConfigPath = Join-Path $ProjectRoot "config.json"
$DistVersionPath = Join-Path $DistDir "VERSION"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$DeployFiles = @(
    "datasharing.exe",
    "datasharing_windows.exe",
    "config.json",
    "GUIDA_UTENTE_DATASHARING.md",
    "VERSION"
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

function Ensure-PackageDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (Test-Path $Path) {
        try {
            Clear-DirectoryContents -Path $Path
        }
        catch {
            throw "Impossibile aggiornare la cartella $Label '$Path'. Chiudere eventuali file aperti e riprovare. Dettaglio: $($_.Exception.Message)"
        }

        return
    }

    try {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    catch {
        throw "Impossibile creare la cartella $Label '$Path'. Dettaglio: $($_.Exception.Message)"
    }
}

function Publish-Package {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Ensure-PackageDirectory -Path $DestinationPath -Label $Label

    try {
        Copy-Item $CliExePath (Join-Path $DestinationPath "datasharing.exe") -Force
        Copy-Item $WindowsExePath (Join-Path $DestinationPath "datasharing_windows.exe") -Force

        if (Test-Path $ConfigPath) {
            Copy-Item $ConfigPath (Join-Path $DestinationPath "config.json") -Force
        }

        if (Test-Path $GuidePath) {
            Copy-Item $GuidePath (Join-Path $DestinationPath "GUIDA_UTENTE_DATASHARING.md") -Force
        }

        if (Test-Path $VersionFilePath) {
            Copy-Item $VersionFilePath (Join-Path $DestinationPath "VERSION") -Force
        }
    }
    catch {
        throw "Impossibile pubblicare il pacchetto nella cartella $Label '$DestinationPath'. Dettaglio: $($_.Exception.Message)"
    }
}

function Get-NextPatchVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    $parts = $Version.Split('.')
    if ($parts.Count -ne 3) {
        throw "Versione non valida '$Version'. Atteso formato major.minor.patch"
    }

    $major = 0
    $minor = 0
    $patch = 0

    if (-not [int]::TryParse($parts[0], [ref]$major)) {
        throw "Major release non valida in '$Version'."
    }

    if (-not [int]::TryParse($parts[1], [ref]$minor)) {
        throw "Minor release non valida in '$Version'."
    }

    if (-not [int]::TryParse($parts[2], [ref]$patch)) {
        throw "Patch release non valida in '$Version'."
    }

    return "$major.$minor.$($patch + 1)"
}

function Update-ApplicationVersion {
    if (-not (Test-Path $VersionFilePath)) {
        throw "File versione non trovato: $VersionFilePath"
    }

    $currentVersion = (Get-Content -Path $VersionFilePath -Raw).Trim()
    if (-not $currentVersion) {
        throw "Il file VERSION e' vuoto: $VersionFilePath"
    }

    $nextVersion = Get-NextPatchVersion -Version $currentVersion
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($VersionFilePath, "$nextVersion`r`n", $utf8NoBom)

    return $nextVersion
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

$newVersion = Update-ApplicationVersion
Write-Host "Versione aggiornata a: $newVersion"

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

    if (Test-Path $ReleaseDir) {
        try {
            Clear-DirectoryContents -Path $ReleaseDir
        }
        catch {
            throw "Impossibile pulire la cartella release '$ReleaseDir'. Chiudere eventuali file aperti e riprovare. Dettaglio: $($_.Exception.Message)"
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
Copy-Item $VersionFilePath $DistVersionPath -Force

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

Publish-Package -DestinationPath $DeployDir -Label "deploy locale"
Publish-Package -DestinationPath $ReleaseDir -Label "release di rete"

Write-Host "Pacchetto deploy pronto in: $DeployDir"
Write-Host "Pacchetto release pronto in: $ReleaseDir"