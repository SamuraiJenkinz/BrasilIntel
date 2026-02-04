<#
.SYNOPSIS
    Manages BrasilIntel scheduled tasks.

.DESCRIPTION
    Provides commands to start, stop, check status, run immediately, view logs,
    and remove BrasilIntel scheduled tasks.

.PARAMETER Action
    Action to perform: start, stop, status, remove, run-now, logs, test

.PARAMETER Category
    Category to target: health, dental, group_life, or all (default: all)

.PARAMETER TaskNamePrefix
    Prefix for scheduled task names (default: BrasilIntel)

.PARAMETER AppPath
    Path to BrasilIntel application directory (default: script location parent)

.PARAMETER LogLines
    Number of log lines to display (default: 50)

.EXAMPLE
    .\manage_service.ps1 -Action status
    Shows status of all scheduled tasks

.EXAMPLE
    .\manage_service.ps1 -Action run-now -Category health
    Runs health category task immediately

.EXAMPLE
    .\manage_service.ps1 -Action logs -Category dental -LogLines 100
    Shows last 100 lines of dental category logs
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "status", "remove", "run-now", "logs", "test")]
    [string]$Action,

    [ValidateSet("health", "dental", "group_life", "all")]
    [string]$Category = "all",

    [string]$TaskNamePrefix = "BrasilIntel",

    [string]$AppPath = (Split-Path -Parent $PSScriptRoot),

    [int]$LogLines = 50
)

# Determine which categories to process
$CategoriesToProcess = if ($Category -eq "all") {
    @("health", "dental", "group_life")
} else {
    @($Category)
}

# Execute action based on command
switch ($Action) {
    "run-now" {
        Write-Host "=== Running Tasks Immediately ===" -ForegroundColor Cyan
        Write-Host ""
        foreach ($Cat in $CategoriesToProcess) {
            $TaskName = "${TaskNamePrefix}_${Cat}"
            try {
                Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
                Write-Host "Started: $TaskName" -ForegroundColor Green
            } catch {
                Write-Host "ERROR: Failed to start $TaskName - $_" -ForegroundColor Red
            }
        }
    }

    "start" {
        Write-Host "=== Enabling Scheduled Tasks ===" -ForegroundColor Cyan
        Write-Host ""
        foreach ($Cat in $CategoriesToProcess) {
            $TaskName = "${TaskNamePrefix}_${Cat}"
            try {
                Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null
                Write-Host "Enabled: $TaskName" -ForegroundColor Green
            } catch {
                Write-Host "ERROR: Failed to enable $TaskName - $_" -ForegroundColor Red
            }
        }
    }

    "stop" {
        Write-Host "=== Disabling Scheduled Tasks ===" -ForegroundColor Cyan
        Write-Host ""
        foreach ($Cat in $CategoriesToProcess) {
            $TaskName = "${TaskNamePrefix}_${Cat}"
            try {
                Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null
                Write-Host "Disabled: $TaskName" -ForegroundColor Green
            } catch {
                Write-Host "ERROR: Failed to disable $TaskName - $_" -ForegroundColor Red
            }
        }
    }

    "status" {
        Write-Host "=== Scheduled Tasks Status ===" -ForegroundColor Cyan
        Write-Host ""
        foreach ($Cat in $CategoriesToProcess) {
            $TaskName = "${TaskNamePrefix}_${Cat}"
            try {
                $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
                $Info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

                Write-Host "Task: $TaskName" -ForegroundColor White

                $StateColor = switch ($Task.State) {
                    "Ready" { "Green" }
                    "Running" { "Yellow" }
                    "Disabled" { "Red" }
                    default { "Gray" }
                }
                Write-Host "  State: $($Task.State)" -ForegroundColor $StateColor
                Write-Host "  Last Run: $($Info.LastRunTime)" -ForegroundColor White
                Write-Host "  Last Result: $($Info.LastTaskResult)" -ForegroundColor White
                Write-Host "  Next Run: $($Info.NextRunTime)" -ForegroundColor White
                Write-Host ""
            } catch {
                Write-Host "Task: $TaskName - NOT FOUND" -ForegroundColor Red
                Write-Host ""
            }
        }
    }

    "remove" {
        Write-Host "=== Removing Scheduled Tasks ===" -ForegroundColor Cyan
        Write-Host ""
        $Confirm = Read-Host "Are you sure you want to remove all BrasilIntel tasks? (yes/no)"
        if ($Confirm -eq "yes") {
            foreach ($Cat in $CategoriesToProcess) {
                $TaskName = "${TaskNamePrefix}_${Cat}"
                try {
                    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
                    Write-Host "Removed: $TaskName" -ForegroundColor Green
                } catch {
                    Write-Host "ERROR: Failed to remove $TaskName - $_" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "Cancelled" -ForegroundColor Yellow
        }
    }

    "logs" {
        Write-Host "=== Viewing Logs ===" -ForegroundColor Cyan
        Write-Host ""
        foreach ($Cat in $CategoriesToProcess) {
            $LogsPath = Join-Path $AppPath "data\logs"
            $LogFiles = Get-ChildItem -Path $LogsPath -Filter "${Cat}_*.log" -ErrorAction SilentlyContinue |
                        Sort-Object LastWriteTime -Descending

            if ($LogFiles) {
                $LatestLog = $LogFiles[0]
                Write-Host "Category: $Cat" -ForegroundColor Yellow
                Write-Host "Log file: $($LatestLog.Name)" -ForegroundColor White
                Write-Host "Last modified: $($LatestLog.LastWriteTime)" -ForegroundColor White
                Write-Host ""
                Write-Host "--- Last $LogLines lines ---" -ForegroundColor Gray
                Get-Content $LatestLog.FullName -Tail $LogLines
                Write-Host ""
            } else {
                Write-Host "No logs found for category: $Cat" -ForegroundColor Red
                Write-Host ""
            }
        }
    }

    "test" {
        Write-Host "=== Testing BrasilIntel ===" -ForegroundColor Cyan
        Write-Host ""

        # Test health check endpoint if server is running
        try {
            $Response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "Health Check Response:" -ForegroundColor Green
            $Response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
            Write-Host ""
        } catch {
            Write-Host "Server not running or health check failed. Starting server..." -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Starting uvicorn server (press Ctrl+C to stop)..." -ForegroundColor Yellow

            Set-Location $AppPath
            & "$AppPath\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
        }
    }
}
