#!/bin/bash

currdir=$PWD
cd ./tests/cmake-examples-master/08-mpi/
rm -rf build
mkdir build
cd build
python3 $currdir/cmakedbg cmake ..
