# cleanup.ps1
# Script to delete heavy folders before git push

Write-Output "Starting cleanup..."

# List of heavy folders to remove
$folders = @(
    "node_modules",
    "whatsapp-bot/node_modules",
    "whatsapp-bot/.local-chromium",
    "whatsapp-bot/.wwebjs_auth",
    "whatsapp-bot/.wwebjs_cache",
    "venv"
)

foreach ($folder in $folders) {
    if (Test-Path $folder) {
        Write-Output "Removing $folder..."
        Remove-Item -Recurse -Force $folder
    } else {
        Write-Output "$folder does not exist, skipping."
    }
}

Write-Output "Done!"
