param (
    [string]$Notebook,
    [int]$Runs = 1,
    [int]$Timeout = 120
)

$Image = "rust-notebook-validator"

if (-not $Notebook) {
    Write-Host "Usage: .\task_runner.ps1 -Notebook colab\001.ipynb [-Runs 1] [-Timeout 120]"
    exit 1
}

# Corrected Docker image existence check
$null = docker image inspect $Image 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker image '$Image' not found."
    Write-Host "Please run 'setup.ps1' if you're using VSCode or 'setup.sh' if you're on Linux/macOS."
    exit 1
}

# Run validator
Write-Host "Validating $Notebook ($Runs runs, $Timeout seconds timeout)..."

docker run --rm `
  -v "${PWD}\colab:/app/colab:ro" `
  -v "${PWD}\tasks:/tasks" `
  $Image `
    "/app/colab/$(Split-Path $Notebook -Leaf)" `
    --runs $Runs `
    --timeout $Timeout
