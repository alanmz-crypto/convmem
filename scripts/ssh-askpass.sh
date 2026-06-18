#!/usr/bin/env bash
# SSH_ASKPASS helper — password in SSHPASS env var (never commit).
exec echo "$SSHPASS"
