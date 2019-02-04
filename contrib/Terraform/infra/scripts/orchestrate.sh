#!/bin/sh

sudo su

echo "*** in orchestrate ***"

./installUtil.sh
./installPythonUtil.sh
./installPG.sh

./installRedis.sh

./setUpCKAN.sh
./setupPG.sh
./configureCKAN.sh
./installSolr.sh

./linkWho.sh
./createDatabase.sh
./startCKAN.sh