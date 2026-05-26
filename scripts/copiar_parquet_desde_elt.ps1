# Copia Parquet/JSON del proyecto anterior a C:\vicuña\data
$origen = "C:\Users\redsito\.cursor\projects\empty-window\globtrade-elt\data"
$destino = "C:\vicuña\data"
if (Test-Path $origen) {
    Copy-Item -Recurse -Force "$origen\*" $destino
    Write-Host "Datos copiados a $destino"
} else {
    Write-Host "No existe $origen — ejecute: python -m etl.run_pipeline"
}
