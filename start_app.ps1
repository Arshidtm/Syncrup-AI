# Nexus AI Engine - Startup Script

Write-Host "Starting Nexus AI Engine..." -ForegroundColor Cyan

# 1. Start Backend (Port 8000)
Write-Host "Launching Backend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& 'd:\Arshid\practice\Nexus_ai_engine\New folder\syncrup_env\Scripts\Activate.ps1'; python src/api_server.py"

# 2. Start Frontend (Port 3000)
Write-Host "Launching Frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "✅ Services started!" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:3000"
