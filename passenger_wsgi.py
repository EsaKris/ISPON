"""Entry point for cPanel 'Setup Python App' (Phusion Passenger)."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from config.wsgi import application  # noqa: E402,F401
