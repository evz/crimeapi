#!/bin/bash
set -e
VENV=/home/crimeweather/sites/crime.static-eric.com
LOGFILE=$VENV/run/gunicorn.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=3
# user/group to run as
USER=crimeweather
GROUP=crimeweather
cd $VENV/checkouts/crimeapi
source $VENV/bin/activate
source /home/crimeweather/.zshenv
test -d $LOGDIR || mkdir -p $LOGDIR
exec $VENV/bin/gunicorn -w $NUM_WORKERS --daemon --bind 127.0.0.1:7777 --user=$USER --group=$GROUP --log-level=debug --log-file=$LOGFILE 2>>$LOGFILE app:app
