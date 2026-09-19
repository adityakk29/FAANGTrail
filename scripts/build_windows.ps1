$ErrorActionPreference = "Stop"
python -m PyInstaller --onefile --name FAANGTrail --paths src --add-data "src/faangtrail/data;faangtrail/data" --clean faangtrail_entry.py
Write-Host "Built dist/FAANGTrail.exe"