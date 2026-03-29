#!/usr/bin/env python3
"""
MutMerge Main Entry Point
Binds the Brain (Core), Memory (DB), and Face (Welcome)
"""

import argparse
import sys
from mutmerge_core import MutMerge
from mutmerge_welcome import show_welcome

def main():
    parser = argparse.ArgumentParser(description="MutMerge: Multi-Arch Mutation Factory")
    
    # Configuration & Database
    parser.add_argument("-c", "--config", default="packages.toml", help="Path to Buffet config")
    parser.add_argument("-d", "--db", default="mutmerge.db", help="Path to SQLite Memory")
    
    # Execution Flags
    parser.add_argument("--arch", help="Climb the ladder for a specific arch (riscv64, arm64, etc.)")
    parser.add_argument("-m", "--max-variants", type=int, default=10, help="Max mutations per package")
    
    # Monitoring & Utility
    parser.add_argument("--stats", action="store_true", help="Show build statistics and exit")
    parser.add_argument("--list-packages", action="store_true", help="List configured Buffet items")
    parser.add_argument("--no-welcome", action="store_true", help="Skip the ASCII animation")

    args = parser.parse_args()

    # 1. Initialize the Core (The Brain)
    try:
        mm = MutMerge(config_path=args.config, db_path=args.db)
    except FileNotFoundError as e:
        print(f"\033[1;31m[!] {e}\033[0m")
        sys.exit(1)

    # 2. Handle Utility Commands first (No animation needed)
    if args.stats:
        mm.show_stats()
        return

    if args.list_packages:
        packages = mm.config.get_packages()
        print(f"\n[ Buffet: {len(packages)} Packages ]")
        for pkg in sorted(packages.keys()):
            print(f"  • {pkg}")
        return

    # 3. Show the "Face" (Welcome Animation)
    if not args.no_welcome:
        show_welcome(db_path=args.db)

    # 4. Check for 'Attention Required' (Previous Failures)
    failed_count = mm.db.get_build_stats().get('FAILED', 0)
    if failed_count > 0:
        print(f"\033[1;33m[!] Warning: {failed_count} previous failures in Memory.\033[0m")
        print("    Check the logs before continuing if these are blocking the ladder.")

    # 5. Run the Mutation Ladder
    if args.arch:
        print(f"\033[1;34m>>> Starting Mutation Ladder for {args.arch}...\033[0m")
        mm.mutate_all_packages(max_variants_per_package=args.max_variants)
    else:
        # If no arch specified, just show help
        parser.print_help()

if __name__ == "__main__":
    main()
            from mutmerge_welcome import show_welcome
            show_welcome()
        except ImportError:
            print("Welcome to MutMerge!")
        parser.print_help()

if __name__ == "__main__":
    main()
