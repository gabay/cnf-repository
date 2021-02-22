#!/bin/bash

BASEDIR=$(dirname $0)/..
CNF_DIR=$BASEDIR/cnf

for f in `find $CNF_DIR -name '*.cnf'`; do gzip -kf $f& done
wait
