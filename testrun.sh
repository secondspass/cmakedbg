#!/bin/bash

# quick script to launch the command line interface on a test cmake directory
currdir=$PWD
cd ./tests/cmake-examples-master/08-mpi/
rm -rf build
mkdir build
cd build
python3 $currdir/cmakedbg -v --cmd cmake ..
