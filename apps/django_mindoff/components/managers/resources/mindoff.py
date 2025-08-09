import argparse
import importlib
import pkgutil
from django_mindoff.components import managers

def main():
    parser = argparse.ArgumentParser(prog="python mindoff.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for _, name, is_pkg in pkgutil.iter_modules(managers.__path__):
        if not is_pkg and name not in {"create_project", "delete_project"}:
            module = importlib.import_module(f"django_mindoff.components.managers.{name}")
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(subparsers)
    args = parser.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
