#!/usr/bin/env bash
set -euo pipefail

AYUCO_HOME="${AYUCO_HOME:-$HOME/.ayuco}"
REPO_URL="https://github.com/franzemil/ayuco.git"

info()  { printf "\033[1;34m▸ %s\033[0m\n" "$*"; }
ok()    { printf "\033[1;32m✔ %s\033[0m\n" "$*"; }
warn()  { printf "\033[1;33m⚠ %s\033[0m\n" "$*"; }
err()   { printf "\033[1;31m✘ %s\033[0m\n" "$*" >&2; exit 1; }

command_exists() { command -v "$1" &>/dev/null; }

install_uv() {
  if command_exists uv; then
    ok "uv already installed ($(uv --version))"
    return
  fi
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command_exists uv || err "uv install failed"
  ok "uv installed ($(uv --version))"
}

install_bwrap() {
  if command_exists bwrap; then
    ok "bwrap already installed"
    return
  fi
  info "Installing bubblewrap (sandbox)..."
  if command_exists apt; then
    sudo apt-get update -qq && sudo apt-get install -y bubblewrap
  elif command_exists dnf; then
    sudo dnf install -y bubblewrap
  elif command_exists pacman; then
    sudo pacman -S --noconfirm bubblewrap
  else
    err "No supported package manager found. Install bubblewrap manually."
  fi
  command_exists bwrap || err "bwrap install failed"
  ok "bwrap installed"
}

clone_or_update() {
  if [ -d "$AYUCO_HOME/.git" ]; then
    info "Updating existing install at $AYUCO_HOME..."
    git -C "$AYUCO_HOME" pull --ff-only || warn "Pull failed — using existing version"
  else
    info "Cloning ayuco to $AYUCO_HOME..."
    rm -rf "$AYUCO_HOME"
    git clone "$REPO_URL" "$AYUCO_HOME"
  fi
  ok "Repository ready at $AYUCO_HOME"
}

setup_project() {
  info "Installing Python dependencies..."
  cd "$AYUCO_HOME"
  uv sync --quiet
  ok "Dependencies installed"

  if [ ! -f config.json ]; then
    cp config.example.json config.json
    warn "Created config.json from config.example.json — edit it with your API keys before running."
  else
    ok "config.json already exists"
  fi
}

print_summary() {
  printf "\n"
  ok "Ayuco installed successfully!"
  printf "\n"
  printf "  \033[1mNext steps:\033[0m\n"
  printf "  1. Edit %s/config.json with your Telegram token and LLM API key\n" "$AYUCO_HOME"
  printf "  2. Run:  cd %s && uv run python main.py\n" "$AYUCO_HOME"
  printf "\n"
}

main() {
  printf "\n\033[1m  Ayuco Installer (Linux)\033[0m\n\n"
  install_uv
  install_bwrap
  clone_or_update
  setup_project
  print_summary
}

main "$@"
