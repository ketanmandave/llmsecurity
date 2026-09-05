param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Question = "What information is available to me?"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:RAG_ACCESS_TOKEN)) {
    throw "Set RAG_ACCESS_TOKEN to a short-lived backend-issued JWT before running."
}

$headers = @{ Authorization = "Bearer $env:RAG_ACCESS_TOKEN" }

Write-Host "Checking liveness..."
Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" | ConvertTo-Json

Write-Host "Checking dependency readiness..."
Invoke-RestMethod -Method Get -Uri "$BaseUrl/ready" | ConvertTo-Json

Write-Host "Checking verified identity..."
Invoke-RestMethod -Method Get -Uri "$BaseUrl/v1/auth/me" -Headers $headers |
    ConvertTo-Json -Depth 5

Write-Host "Running secure RAG query..."
$body = @{ question = $Question; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/v1/query" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body |
    ConvertTo-Json -Depth 8
