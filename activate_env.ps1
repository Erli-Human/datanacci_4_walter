# Activate the virtual environment for datanacci_4_walter project
# Usage: .\activate_env.ps1

$envPath = "..\datanacci_4_walter_env\Scripts\Activate.ps1"

if (Test-Path $envPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & $envPath
    Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
    Write-Host "To run the main application: python main.py" -ForegroundColor Yellow
} else {
    Write-Host "Virtual environment not found at: $envPath" -ForegroundColor Red
    Write-Host "Please make sure the virtual environment is created in the parent directory." -ForegroundColor Red
}
