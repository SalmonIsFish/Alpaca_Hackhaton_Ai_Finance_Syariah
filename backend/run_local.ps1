param(
    [int]$Port = 8000
)

python -m uvicorn local_api:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port
