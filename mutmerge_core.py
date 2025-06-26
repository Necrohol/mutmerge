    def mutate_all_packages(self, max_variants_per_package: int = 50, use_queue: bool = False):#!/usr/bin/env python3
"""
Main MutMerge class - coordinates all components
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

from .database import MutMergeDB
from .config import ConfigManager
from .use_flags import USEFlagGenerator, USEFlagParser
from .builder import PackageBuilder, BuildResult


class MutMerge:
    """Main mutmerge class"""
    
    def __init__(self, config_path: Optional[str] = None, db_path: str = "mutmerge.db",
                 chroot_path: Optional[str] = None, use_docker: bool = False, 
                 repos_config: Optional[str] = None, use_binary_gentoo: bool = True):
        self.config = ConfigManager(config_path)
        self.db = MutMergeDB(db_path)
        self.builder = PackageBuilder(chroot_path, use_docker, use_binary_gentoo)
        self.repos_config = repos_config
        
        # Setup logging
        self._setup_logging()
        
        # Load repository manager if repos config exists
        self.repo_manager = self._load_repo_manager()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('mutmerge.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_repo_manager(self):
        """Load repository manager if available"""
        if not self.repos_config or not os.path.exists(self.repos_config):
            return None
        
        try:
            sys.path.append(str(Path(__file__).parent))
            from repo_manager import RepositoryManager  # type: ignore
            return RepositoryManager(self.repos_config)
        except ImportError:
            self.logger.warning("Repository manager not available")
            return None
    
    def mutate_package(self, package: str, max_variants: int = 50):
        """Mutate a single package through various USE flag combinations"""
        self.logger.info(f"Starting mutation testing for {package}")
        
        # Get package configuration
        pkg_config = self.config.get_package_config(package)
        if not pkg_config:
            self.logger.error(f"Package {package} not found in configuration")
            return
        
        # Test build environment first
        if not self.builder.test_build_environment():
            self.logger.error("Build environment test failed")
            return
        
        # Get base USE flags
        base_flags = self.builder.get_current_use_flags(package)
        
        # Get test flags from config
        test_flags = self._extract_test_flags(pkg_config)
        
        # Generate combinations
        generator = USEFlagGenerator(base_flags, test_flags, max_variants)
        combinations = generator.generate_combinations()
        
        self.logger.info(f"Generated {len(combinations)} USE flag combinations for {package}")
        
        # Test each combination
        self._test_combinations(package, combinations)
        
        # Cleanup
        self.builder.cleanup_build_artifacts(package)
        
        self.logger.info(f"Mutation testing complete for {package}")
    
    def _extract_test_flags(self, pkg_config: dict) -> list:
        """Extract test flags from package configuration"""
        test_flags = []
        for key, value in pkg_config.items():
            if key.startswith('USE'):
                if isinstance(value, str):
                    test_flags.extend(value.split())
                elif isinstance(value, list):
                    test_flags.extend(value)
        return test_flags
    
    def _test_combinations(self, package: str, combinations: list):
        """Test all USE flag combinations for a package"""
        success_count = 0
        skip_count = 0
        
        for i, use_combo in enumerate(combinations):
            use_string = USEFlagParser.format_use_flags(use_combo)
            
            # Check if we should skip this combination
            if self.db.should_skip_combination(package, use_string):
                self.logger.info(f"Skipping known bad combination: {use_string}")
                skip_count += 1
                continue
            
            self.logger.info(f"Testing combination {i+1}/{len(combinations)}: {use_string}")
            
            # Build the package variant
            success, error_log, build_time = self.builder.build_package_variant(package, use_combo)
            
            # Create build result
            result = BuildResult(package, use_string, success, build_time, error_log)
            
            # Record result
            self.db.record_build(
                package, use_string, result.get_error_category(), 
                build_time, error_log if not success else None
            )
            
            if success:
                success_count += 1
                self.logger.info(f"✓ Build successful in {build_time:.2f}s")
            else:
                self.logger.error(f"✗ Build failed in {build_time:.2f}s: {error_log[:100]}...")
                
                # Add to skip list if it's a dependency issue
                if result.is_dependency_error():
                    self.db.add_skip_combination(package, use_string, "Dependency conflict")
        
        self.logger.info(f"Results: {success_count} successful, {skip_count} skipped out of {len(combinations)} combinations")
    
    def mutate_all_packages(self, max_variants_per_package: int = 50):
        """Mutate all packages in configuration"""
        packages = self.config.get_packages()
        
        self.logger.info(f"Starting mutation testing for {len(packages)} packages")
        
        for package in packages:
            try:
                self.mutate_package(package, max_variants_per_package)
            except Exception as e:
                self.logger.error(f"Error processing {package}: {e}")
        
        self.logger.info("Mutation testing complete for all packages")
    
    def show_stats(self, package: Optional[str] = None):
        """Show build statistics"""
        stats = self.db.get_build_stats(package)
        
        if package:
            print(f"\nBuild statistics for {package}:")
        else:
            print("\nOverall build statistics:")
        
        total = sum(stats.values())
        for status, count in stats.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        print(f"  Total builds: {total}")
    
    def show_recent_builds(self, package: Optional[str] = None, limit: int = 10):
        """Show recent builds"""
        builds = self.db.get_recent_builds(package, limit)
        
        print(f"\nRecent builds (last {limit}):")
        for build in builds:
            pkg, use_flags, status, timestamp, build_time = build
            print(f"  {pkg}: {status} ({build_time:.2f}s) - {use_flags[:50]}...")
    
    def validate_configuration(self) -> bool:
        """Validate the current configuration"""
        try:
            packages = self.config.get_packages()
            if not packages:
                self.logger.error("No packages found in configuration")
                return False
            
            self.logger.info(f"Configuration valid: {len(packages)} packages configured")
            return True
        
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
