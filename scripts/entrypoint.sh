#!/bin/bash

. /kb/deployment/user-env.sh

python ./scripts/prepare_deploy_cfg.py ./deploy.cfg ./work/config.properties

if [ -f ./work/token ] ; then
  export KB_AUTH_TOKEN=$(<./work/token)
fi

if [ $# -eq 0 ] ; then
  sh ./scripts/start_server.sh
elif [ "${1}" = "test" ] ; then
  echo "Run Tests"
  make test
elif [ "${1}" = "async" ] ; then
  sh ./scripts/run_async.sh
elif [ "${1}" = "init" ] ; then
  echo "Initialize module"
  # mkdir -p /data/anviodb
  # cd /data/anviodb

  # Ideally would download this here but then Anvio can't find the database later
  # echo "Running anvi-setup-scg-taxonomy"
  # anvi-setup-scg-taxonomy -T 1

  # echo "Running anvi-setup-ncbi-cogs" # need BLAST tools
  # anvi-setup-ncbi-cogs -T 4 --just-do-it --cog-data-dir /data/anviodb/COG
  # echo "Running anvi-setup-pfams" 
  # anvi-setup-pfams --pfam-data-dir /data/anviodb/Pfam
  # echo "Running anvi-setup-kegg-kofams" # yaml update
  # anvi-setup-kegg-kofams --download-from-kegg --kegg-data-dir /data/anviodb/KEGG
  # echo "anvi-setup-interacdome"
  # anvi-setup-interacdome --interacdome-data-dir /data/anviodb/Interacdome
  # echo "anvi-setup-pdb-database"
  # anvi-setup-pdb-database -T 1 --pdb-database-path /data/anviodb/PDB.db
  # cd /data/anviodb
  # if [ -d "/data/anviodb/COG" -a -d "/data/anviodb/Pfam" -a -d "/data/anviodb/KEGG" ] ; then
  #   echo "DATA DOWNLOADED SUCCESSFULLY"
  # touch /data/__READY__
  # else
  #   echo "Init failed"
  # fi
elif [ "${1}" = "bash" ] ; then
  bash
elif [ "${1}" = "report" ] ; then
  export KB_SDK_COMPILE_REPORT_FILE=./work/compile_report.json
  make compile
else
  echo Unknown
fi
