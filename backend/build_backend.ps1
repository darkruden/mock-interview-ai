# build_backend.ps1
Write-Host "🚀 Iniciando Build do Backend..." -ForegroundColor Cyan

$srcDir = "src"
$buildDir = "../build_package"

# 1. Limpa e Recria a pasta de build
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
}
New-Item -ItemType Directory -Path $buildDir | Out-Null

# 2. Copia seu código fonte para lá
Copy-Item -Path "$srcDir\*" -Destination $buildDir -Recurse

# 3. Instala dependências Linux-Compatible na pasta de build
# (Nota: Mantemos as flags de compatibilidade por causa do seu Python 3.14 e Windows)
Write-Host "📦 Instalando dependências (Cross-Platform)..." -ForegroundColor Yellow
pip install --target $buildDir --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --upgrade -r requirements.txt | Out-Null

Write-Host "✅ Build concluído em: $buildDir" -ForegroundColor Green
Write-Host "Agora pode rodar o Terraform!" -ForegroundColor Green