#!/usr/bin/env bash

# Build
./build.sh

# Push on PyPi
twine upload dist/*

# Notify on slack
sed "s/USER/${USER^}/" $WORKSPACE/slack.json > $WORKSPACE/.slack.json
sed -i.bak "s/VERSION/$(git describe)/" $WORKSPACE/.slack.json
curl -k -X POST --data-urlencode payload@$WORKSPACE/.slack.json https://hbps1.chuv.ch/slack/dev-activity
rm -f $WORKSPACE/.slack.json
rm -f $WORKSPACE/.slack.json.bak
