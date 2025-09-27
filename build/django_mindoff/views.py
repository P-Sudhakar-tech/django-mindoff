# views.py
import argparse
import importlib

from .components import managers


def main():
    parser = argparse.ArgumentParser(prog="django-mindoff")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ["init", "nuke"]:
        module = importlib.import_module(f"django_mindoff.components.managers.{name}")
        if hasattr(module, "register_subcommand"):
            module.register_subcommand(subparsers)
    args = parser.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()
