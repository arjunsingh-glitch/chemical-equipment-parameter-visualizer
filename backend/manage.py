#!/usr/bin/env python
"""
Simple manage.py for the FOSSEE Chemical Equipment Parameter Visualizer backend.

This is the standard Django entry point used to run the development server,
apply migrations, and perform other project management tasks.
"""
import os
import sys


def main() -> None:
    """Run administrative tasks."""
    # We keep the settings module name explicit so it is easy to find/change.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # This block is helpful when Django is not installed in the current env.
        raise ImportError(
            "Couldn't import Django. Make sure it is installed and available "
            "on your PYTHONPATH, and that the virtual environment is activated."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

