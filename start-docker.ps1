$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
docker compose up --build -d
docker compose ps
