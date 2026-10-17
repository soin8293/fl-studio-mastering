<#
.SYNOPSIS
Render one saved FL project through its native command line, preserving existing sessions.
.DESCRIPTION
Refuses to launch while FL is already running. Stops only its own completed render
process. A timeout or dialog leaves that process intact for diagnosis.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Project,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$FlExe = (Join-Path $env:ProgramFiles 'Image-Line\FL Studio 21\FL64.exe'),
    [string]$RestoreProject,
    [string]$ProjectTitle,
    [ValidateRange(0,86400)][double]$ExpectedDurationSeconds = 0,
    [ValidateRange(0.01,300)][double]$DurationToleranceSeconds = 2,
    [ValidateRange(15,7200)][int]$TimeoutSeconds = 300
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath $Project).ProviderPath
$executablePath = (Resolve-Path -LiteralPath $FlExe).ProviderPath
if ([IO.Path]::GetExtension($projectPath) -ne '.flp') { throw 'Supply a saved FLP project.' }
$outputPath = [IO.Path]::GetFullPath($OutputDirectory)
$wavePath = Join-Path $outputPath ([IO.Path]::GetFileNameWithoutExtension($projectPath) + '.wav')
$finishedTitles = @(
    ([IO.Path]::GetFileName($projectPath) + ' - FL Studio 21'),
    ([IO.Path]::GetFileNameWithoutExtension($projectPath) + ' - FL Studio 21')
)
if (-not [string]::IsNullOrWhiteSpace($ProjectTitle)) {
    $finishedTitles += ($ProjectTitle + ' - FL Studio 21')
}
if (Test-Path -LiteralPath $wavePath) { throw "Refusing to overwrite $wavePath" }
if ($RestoreProject) { $restorePath = (Resolve-Path -LiteralPath $RestoreProject).ProviderPath }
$processName = [IO.Path]::GetFileNameWithoutExtension($executablePath)
if (Get-Process -Name $processName -ErrorAction SilentlyContinue) {
    throw 'FL is already running. Preserve and close the current session before rendering; no process was stopped.'
}
$null = Get-Command ffprobe -ErrorAction Stop
$null = Get-Command ffmpeg -ErrorAction Stop
$null = New-Item -ItemType Directory -Force -Path $outputPath
# Windows paths cannot contain double quotes; each path is a distinct quoted argument.
$arguments = '/R /Ewav /O"{0}" "{1}"' -f $outputPath, $projectPath
$renderProcess = Start-Process -FilePath $executablePath -ArgumentList $arguments `
    -WorkingDirectory (Split-Path -Parent $executablePath) -WindowStyle Hidden -PassThru
$timer = [Diagnostics.Stopwatch]::StartNew()
$previousLength = -1L
$stableChecks = 0
$completed = $false
while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    Start-Sleep -Milliseconds 1000
    $renderProcess.Refresh()
    $file = Get-Item -LiteralPath $wavePath -ErrorAction SilentlyContinue
    if ($file -and $file.Length -gt 44) {
        if ($file.Length -eq $previousLength) { $stableChecks++ } else { $stableChecks = 0 }
        $previousLength = $file.Length
        $titleReady = $renderProcess.HasExited -or (
            $renderProcess.MainWindowTitle -in $finishedTitles)
        if ($stableChecks -ge 2 -and $titleReady) {
            $probeOutput = & ffprobe -v error -show_entries format=duration -of json $wavePath 2>&1
            if ($LASTEXITCODE -ne 0) { continue }
            $probe = ($probeOutput -join "`n") | ConvertFrom-Json
            if ([double]$probe.format.duration -le 0) { continue }
            if ($ExpectedDurationSeconds -gt 0 -and
                [Math]::Abs([double]$probe.format.duration - $ExpectedDurationSeconds) -gt $DurationToleranceSeconds) {
                throw "Export duration $($probe.format.duration)s does not match expected $($ExpectedDurationSeconds)s (+/- $($DurationToleranceSeconds)s); task process PID $($renderProcess.Id) was left intact."
            }
            $null = & ffmpeg -hide_banner -loglevel error -xerror -i $wavePath -map 0:a:0 -f null NUL 2>&1
            if ($LASTEXITCODE -ne 0) { continue }
            $completed = $true
            break
        }
    }
    if ($renderProcess.HasExited -and (-not $file -or $file.Length -le 44)) {
        throw "FL render exited without a complete WAV (PID $($renderProcess.Id))."
    }
}
if (-not $completed) {
    throw "Render timed out; task process PID $($renderProcess.Id) was left intact. Inspect it before retrying."
}
if (-not $renderProcess.HasExited) { Stop-Process -Id $renderProcess.Id -ErrorAction Stop }
$restoredId = $null
if ($restorePath) {
    $restored = Start-Process -FilePath $executablePath -ArgumentList ('"{0}"' -f $restorePath) `
        -WorkingDirectory (Split-Path -Parent $executablePath) -WindowStyle Hidden -PassThru
    $restoredId = $restored.Id
}
[pscustomobject]@{ Wave=$wavePath; DurationSeconds=[double]$probe.format.duration;
                  RenderPid=$renderProcess.Id; RestoredPid=$restoredId } | ConvertTo-Json
