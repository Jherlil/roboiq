#!/bin/bash
set -e

echo "=== Atualizando e instalando dependências básicas ==="
sudo apt-get update
sudo apt-get install -y build-essential wget

echo "=== Baixando e compilando TA-Lib C ==="
cd ~
rm -rf ta-lib ta-lib-0.4.0 ta-lib-0.4.0-src.tar.gz
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzvf ta-lib-0.4.0-src.tar.gz
cd ta-lib-0.4.0
./configure --prefix=/usr
make -j$(nproc)
sudo make install

echo "=== Voltando para o bot ==="
cd ~/my_bot

echo "=== Definindo paths para libta_lib ==="
export LD_LIBRARY_PATH=/usr/lib
export LIBRARY_PATH=/usr/lib
export CPATH=/usr/include

echo "=== Instalando TA-Lib Python wrapper ==="
python3 -m pip install --no-cache-dir --no-build-isolation TA-Lib

echo "=== Testando instalação ==="
python3 -c "import talib; print('TA-Lib OK!', talib.__version__)"
