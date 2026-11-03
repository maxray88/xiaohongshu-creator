#!/bin/bash
# clean-env: strip gateway vars (e.g. ANTHROPIC_BASE_URL) that break `claude` CLI login; run command with a clean terminal-like env.
exec env -i \
  HOME="$HOME" \
  USER="$USER" \
  LOGNAME="$LOGNAME" \
  PATH="$PATH" \
  TERM="${TERM:-xterm-256color}" \
  SHELL=/bin/zsh \
  LANG=en_US.UTF-8 \
  "$@"
