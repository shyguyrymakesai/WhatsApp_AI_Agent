Write-Host "Starting fresh setup..."

# Remove old venv safely
if (Test-Path ".\venv") {
    Write-Host "Removing old venv..."
    try {
        Remove-Item -Recurse -Force ".\venv"
    } catch {
        Write-Host "⚠️ Failed to delete venv, please check manually." -ForegroundColor Yellow
    }
}

# Create new venv
Write-Host "Creating new venv..."
python -m venv venv

if (!(Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Venv creation failed. Exiting." -ForegroundColor Red
    exit
}

# Activate venv
Write-Host "Activating venv..."
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..."
pip install -r requirements.txt

Write-Host "✅ Setup complete. You're ready to code!" -ForegroundColor Green
