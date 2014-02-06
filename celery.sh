#!/bin/bash
set -e
VENV=/home/crimeweather/sites/crime.static-eric.com
LOGFILE=$VENV/run/celery.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=3
# user/group to run as
source /home/crimeweather/.zshenv
USER=crimeweather
GROUP=crimeweather
cd $VENV/checkouts/crimeweatherupdater
source $VENV/bin/activate
test -d $LOGDIR || mkdir -p $LOGDIR
exec $VENV/bin/celery -A tasks worker -B --loglevel=info --logfile=$LOGFILE

