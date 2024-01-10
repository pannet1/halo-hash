#!/bin/env sh

# Define the session name
session_name="zerodte"

# Check if the session exists
if tmux has-session -t "$session_name" 2>/dev/null; then
  echo "Session $session_name already exists. Attaching to it."
  tmux attach -t "$session_name"
else
  # If the session doesn't exist, create it
  echo "Creating and attaching to session $session_name."
  tmux new-session -d -s "$session_name" 
  tmux send-keys -t "$session_name" "cd ~/py/zero-dte/zero_dte" C-m 
  tmux send-keys -t "$session_name" "git reset --hard & git pull" C-m
  tmux send-keys -t "$session_name" "pwd" C-m 
  tmux send-keys -t "$session_name" "python3 zerodte.py" C-m
  tmux attach -t "$session_name"
fi

