#!/bin/bash

# quick script to launch the command line interface on a test cmake directory
# (when in activated poetry environment)
currdir=$PWD
poetry install
cd ./tests/cmake-examples-master/08-mpi/
rm -rf build
mkdir build
cd build
#python3  $currdir/cmakedbg/__main__.py -v --cmd cmake ..
cmakedbg --cmd cmake ..
