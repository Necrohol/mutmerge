import time
from mutmerge_database import MutMergeDB
from mutmerge_config import ConfigManager
from mutmerge_builder import MutMergeBuilder

class MutMerge:
    def __init__(self, config_path="packages.toml", db_path="mutmerge.db"):
        self.db = MutMergeDB(db_path)
        self.config = ConfigManager(config_path)
        self.builder = MutMergeBuilder()

    def mutate_all_packages(self, arch, max_variants_per_package=10):
        """Climbs the ladder by building the 'Lightest' mutations first."""
        packages = self.config.get_packages()
        
        # Sort packages by 'Weight' (historical build time) from SQLite
        # New/Unknown packages get weight 0 (top of the list)
        sorted_pkgs = sorted(
            packages.keys(), 
            key=lambda p: self.db.get_package_weight(p, arch)
        )

        for pkg in sorted_pkgs:
            print(f"🧬 Mutating DNA: {pkg} for {arch}...")
            start_time = time.time()
            
            # 1. Muscle: Trigger the Podman/SSH Build
            # Returns 'SUCCESS' or 'FAILED'
            result = self.builder.run_build(pkg, arch, self.config.get_flags(pkg))
            
            duration = int(time.time() - start_time)
            
            # 2. Memory: Record the mutation outcome and cost
            self.db.record_build(
                package=pkg,
                arch=arch,
                status=result,
                duration=duration
            )
            
            if result == "SUCCESS":
                print(f"✅ Mutation Stable: {pkg} added to Showroom.")
            else:
                print(f"⚠️ Mutation Inviable: {pkg} needs Attention.")

