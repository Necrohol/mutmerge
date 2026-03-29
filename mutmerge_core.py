#!/usr/bin/env python3
import time
from mutmerge_database import MutMergeDB
from mutmerge_config import ConfigManager
from mutmerge_builder import MutMergeBuilder

class MutMerge:
    """
    The Brain: Orchestrates the mutation logic.
    Decides the build order based on historical cost (duration).
    """
    def __init__(self, config_path="packages.toml", db_path="mutmerge.db"):
        self.db = MutMergeDB(db_path)
        self.config = ConfigManager(config_path)
        self.builder = MutMergeBuilder()

    def show_stats(self):
        """Displays the Memory of the Squid: Success vs Failure rates."""
        stats = self.db.get_build_stats()
        print("\n📊 [ Mutation Memory Statistics ]")
        print(f"  ✅ Stable Mutations: {stats.get('SUCCESS', 0)}")
        print(f"  ❌ Inviable DNAs:    {stats.get('FAILED', 0)}")
        
        avg_time = self.db.get_global_avg_duration()
        print(f"  🕒 Avg Synthesis:    {avg_time}s")

    def _generate_mutation_variants(self, pkg_name):
        """
        Extracts USE flag combinations from the Buffet (Config).
        Supports 'Thin' and 'Max' presets defined in TOML.
        """
        pkg_data = self.config.get_package_data(pkg_name)
        # Returns a list of strings like ["+ssl -nls", "+ssl +nls +xml", "minimal"]
        return pkg_data.get("variants", ["default"])

    def mutate_all_packages(self, arch, max_variants_per_package=10):
        """
        The Ladder: Builds the 'Lightest' packages first to 
        populate the Showroom as fast as possible.
        """
        all_packages = self.config.get_packages()
        
        # 1. Sort by Weight (Average historical duration)
        # New packages (Weight 0) move to the front of the line.
        sorted_queue = sorted(
            all_packages.keys(),
            key=lambda p: self.db.get_package_weight(p, arch)
        )

        print(f"🧬 Brain: Optimized Queue for {arch} (Fastest First).")

        for pkg in sorted_queue:
            variants = self._generate_mutation_variants(pkg)
            
            # Limit mutations to keep the ladder manageable
            for variant_flags in variants[:max_variants_per_package]:
                print(f"🧪 Attempting Mutation: {pkg} [{variant_flags}]")
                
                # 2. Call the Muscle (Podman/Alpine)
                # This returns the status and the actual time taken
                status, duration = self.builder.run_build(pkg, arch, variant_flags)
                
                # 3. Record in Memory
                self.db.record_build(
                    package=pkg,
                    arch=arch,
                    status=status,
                    duration=duration,
                    flags=variant_flags
                )

                if status == "SUCCESS":
                    print(f"✨ Mutation Stable! ({duration}s)")
                else:
                    print(f"💀 Mutation Failed. Logged to Memory.")

        print(f"🏁 Brain: Mutation Ladder complete for {arch}.")
