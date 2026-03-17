#!/usr/bin/env bash

docker buildx build --platform linux/amd64 -t srmoocow/slack-groupme-bridge:latest --push python/
