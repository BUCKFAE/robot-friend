set windows-shell := ["powershell", "-NoProfile", "-Command"]

mod arduino
mod python
mod pi

_default:
  just --list
