Write-Host "Starting deluxe cleanup..."

# Define folders to clean
$foldersToDelete = @(
    "node_modules",
    "whatsapp-bot/node_modules",
    "whatsapp-bot/.local-chromium",
    "whatsapp-bot/.wwebjs_auth",
    "whatsapp-bot/.wwebjs_cache",
    "venv"
)

# Delete folders if they exist
foreach ($folder in $foldersToDelete) {
    if (Test-Path $folder) {
        Write-Host "Removing $folder..."
        Remove-Item -Recurse -Force $folder
    } else {
        Write-Host "$folder does not exist, skipping."
    }
}

# Clean Git objects and garbage
Write-Host "Cleaning git history..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Stage and commit changes
Write-Host "Adding and committing cleanup changes..."
git add -A
git commit -m "Automated cleanup before push" | Out-Null

# Ask user if they want to force push
$push = Read-Host "Do you want to force push to origin/main? (y/n)"
if ($push -eq "y") {
    Write-Host "Force pushing..."
    git push origin main --force
} else {
    Write-Host "Skipping force push."
}

Write-Host "Deluxe cleanup complete!"
