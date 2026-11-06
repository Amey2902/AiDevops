# DevOpsAI Development Startup Script (Windows PowerShell)

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Starting DevOpsAI Incident Investigation Platform" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Start Django Backend
Write-Host "`n[1/2] Starting Django REST Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd backend; ..\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000"

# 2. Start React Frontend
Write-Host "`n[2/2] Starting React Vite Frontend on http://localhost:3000..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`nDevOpsAI is launching!" -ForegroundColor Green
Write-Host "Frontend Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "Backend API Hub:   http://127.0.0.1:8000/api/incidents/" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Cyan

