#!/usr/bin/env python3
# mutmerge.py
import argparse
import sys
from mutmerge_core import MutMerge
from mutmerge_database import MutMergeDB
from mutmerge_config import ConfigManager

def main():
    parser = argparse.ArgumentParser(description="MutMerge: Multi-Arch Mutation Builder")
    parser.add_argument("--arch", help="Target architecture (e.g., riscv64, arm64)")
    parser.add_argument("--max-variants", type=int, default=10, help="Max USE combos per package")
    parser.add_argument("--stats", action="store_true", help="Show build statistics")
    parser.add_argument("--list-packages", action="store_true", help="List configured packages")
    parser.add_argument("--config", default="packages.toml", help="Path to config file")
    parser.add_argument("--db", default="mutmerge.db", help="Path to SQLite DB")

    args = parser.parse_args()

    # Initialize the "Brain"
    mm = MutMerge(config_path=args.config, db_path=args.db)

    if args.stats:
        mm.show_stats()
    elif args.list_packages:
        packages = mm.config.get_packages()
        print(f"Loaded {len(packages)} packages from {args.config}:")
        for pkg in sorted(packages.keys()):
            print(f"  - {pkg}")
    elif args.arch:
        print(f">>> Starting Mutation Ladder for {args.arch}...")
        # This calls the logic in mutmerge_core.py
        mm.mutate_all_packages(max_variants_per_package=args.max_variants)
    else:
        # Default behavior: Show welcome and help
        try:
            from mutmerge_welcome import show_welcome
            show_welcome()
        except ImportError:
            print("Welcome to MutMerge!")
        parser.print_help()

if __name__ == "__main__":
    main()
