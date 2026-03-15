#!/usr/bin/env bash

docker build -t slack-groupme-bridge app-docker/
docker tag slack-groupme-bridge:latest srmoocow/slack-groupme-bridge:latest
docker push srmoocow/slack-groupme-bridge:latest
