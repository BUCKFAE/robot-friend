set windows-shell := ["powershell", "-NoProfile", "-Command"]

mod arduino
mod python

_default:
  just --list
