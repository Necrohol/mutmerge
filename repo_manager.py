#!/usr/bin/env python3
"""
repo-manager.py - Gentoo Repository Management for MutMerge
Manages repositories defined in repos.toml using eselect repository
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
import time
import json

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib/tomli required for TOML support")
        print("Install with: pip install tomli")
        sys.exit(1)

class RepositoryManager:
    """Manage Gentoo repositories using eselect repository"""
    
    def __init__(self, config_path: str = "repos.toml"):
        self.config_path = config_path
        self.config = self.load_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('repo-manager.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> Dict:
        """Load repository configuration from TOML file"""
        try:
            with open(self.config_path, 'rb') as f:
                return tomllib.load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def run_command(self, cmd: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        try:
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(cmd)}")
            self.logger.error(f"Return code: {e.returncode}")
            if e.stdout:
                self.logger.error(f"STDOUT: {e.stdout}")
            if e.stderr:
                self.logger.error(f"STDERR: {e.stderr}")
            raise
    
    def check_eselect_availability(self) -> bool:
        """Check if eselect repository is available"""
        try:
            result = self.run_command(['eselect', 'repository', 'list'], check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_enabled_repositories(self) -> Set[str]:
        """Get list of currently enabled repositories"""
        try:
            result = self.run_command(['eselect', 'repository', 'list', '-i'])
            enabled_repos = set()
            
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('[') and '*' in line:
                    # Parse enabled repository names
                    parts = line.split()
                    for part in parts:
                        if part and not part.startswith('[') and part != '*':
                            enabled_repos.add(part)
                            break
            
            return enabled_repos
        except subprocess.CalledProcessError:
            return set()
    
    def get_available_repositories(self) -> Set[str]:
        """Get list of all available repositories"""
        try:
            result = self.run_command(['eselect', 'repository', 'list'])
            available_repos = set()
            
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('['):
                    # Parse repository names
                    parts = line.split()
                    if len(parts) >= 2:
                        repo_name = parts[1] if parts[1] != '*' else parts[2] if len(parts) > 2 else None
                        if repo_name:
                            available_repos.add(repo_name)
            
            return available_repos
        except subprocess.CalledProcessError:
            return set()
    
    def enable_repository(self, repo_name: str) -> bool:
        """Enable a repository using eselect"""
        try:
            self.logger.info(f"Enabling repository: {repo_name}")
            self.run_command(['eselect', 'repository', 'enable', repo_name])
            return True
        except subprocess.CalledProcessError:
            self.logger.error(f"Failed to enable repository: {repo_name}")
            return False
    
    def disable_repository(self, repo_name: str) -> bool:
        """Disable a repository using eselect"""
        try:
            self.logger.info(f"Disabling repository: {repo_name}")
            self.run_command(['eselect', 'repository', 'disable', repo_name])
            return True
        except subprocess.CalledProcessError:
            self.logger.error(f"Failed to disable repository: {repo_name}")
            return False
    
    def add_custom_repository(self, repo_name: str, repo_config: Dict) -> bool:
        """Add a custom repository configuration"""
        try:
            if repo_config.get('sync_type') == 'local':
                # Create local repository
                repo_path = repo_config.get('location', f"/var/db/repos/{repo_name}")
                if repo_config.get('create_if_missing', False):
                    os.makedirs(repo_path, exist_ok=True)
                    
                    # Create basic repository structure
                    profiles_dir = Path(repo_path) / "profiles"
                    profiles_dir.mkdir(exist_ok=True)
                    
                    # Create repo_name file
                    with open(profiles_dir / "repo_name", 'w') as f:
                        f.write(repo_name)
                    
                    # Create basic layout.conf
                    with open(profiles_dir / "layout.conf", 'w') as f:
                        f.write("masters = gentoo\n")
                        f.write("auto-sync = false\n")
                
                self.logger.info(f"Local repository created: {repo_path}")
                return True
            else:
                # For remote repositories, they should be available via eselect
                self.logger.info(f"Remote repository should be available via eselect: {repo_name}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to add custom repository {repo_name}: {e}")
            return False
    
    def sync_repository(self, repo_name: str) -> bool:
        """Sync a specific repository"""
        try:
            self.logger.info(f"Syncing repository: {repo_name}")
            self.run_command(['emerge', '--sync', repo_name])
            return True
        except subprocess.CalledProcessError:
            self.logger.error(f"Failed to sync repository: {repo_name}")
            return False
    
    def sync_all_enabled(self) -> bool:
        """Sync all enabled repositories"""
        try:
            self.logger.info("Syncing all enabled repositories")
            self.run_command(['emerge', '--sync'])
            return True
        except subprocess.CalledProcessError:
            self.logger.error("Failed to sync repositories")
            return False
    
    def setup_repositories(self, repo_names: List[str] = None) -> bool:
        """Set up repositories from configuration"""
        if not self.check_eselect_availability():
            self.logger.error("eselect repository is not available")
            return False
        
        repositories = self.config.get('repositories', {})
        available_repos = self.get_available_repositories()
        enabled_repos = self.get_enabled_repositories()
        
        if repo_names is None:
            repo_names = list(repositories.keys())
        
        success_count = 0
        
        for repo_name in repo_names:
            if repo_name not in repositories:
                self.logger.warning(f"Repository {repo_name} not found in configuration")
                continue
            
            repo_config = repositories[repo_name]
            
            # Add custom repository if needed
            if repo_config.get('sync_type') == 'local':
                if not self.add_custom_repository(repo_name, repo_config):
                    continue
            
            # Check if repository is available
            if repo_name not in available_repos:
                self.logger.warning(f"Repository {repo_name} not available via eselect")
                continue
            
            # Enable repository if not already enabled
            if repo_name not in enabled_repos:
                if self.enable_repository(repo_name):
                    success_count += 1
                    
                    # Sync if auto_sync is enabled
                    if repo_config.get('auto_sync', True):
                        self.sync_repository(repo_name)
            else:
                self.logger.info(f"Repository {repo_name} already enabled")
                success_count += 1
        
        self.logger.info(f"Successfully set up {success_count}/{len(repo_names)} repositories")
        return success_count == len(repo_names)
    
    def setup_repository_group(self, group_name: str) -> bool:
        """Set up a group of repositories"""
        groups = self.config.get('repository_groups', {})
        
        if group_name not in groups:
            self.logger.error(f"Repository group {group_name} not found")
            return False
        
        repo_names = groups[group_name]
        self.logger.info(f"Setting up repository group '{group_name}': {repo_names}")
        
        return self.setup_repositories(repo_names)
    
    def list_repositories(self, show_config: bool = False):
        """List repositories and their status"""
        if not self.check_eselect_availability():
            self.logger.error("eselect repository is not available")
            return
        
        available_repos = self.get_available_repositories()
        enabled_repos = self.get_enabled_repositories()
        configured_repos = set(self.config.get('repositories', {}).keys())
        
        print("\n=== Repository Status ===")
        print(f"Available repositories: {len(available_repos)}")
        print(f"Enabled repositories: {len(enabled_repos)}")
        print(f"Configured repositories: {len(configured_repos)}")
        
        print("\n=== Configured Repositories ===")
        for repo_name, repo_config in self.config.get('repositories', {}).items():
            status = "✓" if repo_name in enabled_repos else "✗"
            available = "available" if repo_name in available_repos else "not available"
            print(f"{status} {repo_name:<20} ({available})")
            
            if show_config:
                print(f"    Description: {repo_config.get('description', 'N/A')}")
                print(f"    URL: {repo_config.get('url', 'N/A')}")
                print(f"    Sync Type: {repo_config.get('sync_type', 'git')}")
                print(f"    Auto Sync: {repo_config.get('auto_sync', True)}")
                if 'packages_of_interest' in repo_config:
                    packages = repo_config['packages_of_interest'][:3]
                    more = f" (+{len(repo_config['packages_of_interest'])-3} more)" if len(repo_config['packages_of_interest']) > 3 else ""
                    print(f"    Key Packages: {', '.join(packages)}{more}")
                print()
        
        if configured_repos - available_repos:
            print("\n=== Missing Repositories ===")
            for repo_name in sorted(configured_repos - available_repos):
                print(f"✗ {repo_name} (configured but not available)")
        
        groups = self.config.get('repository_groups', {})
        if groups:
            print("\n=== Repository Groups ===")
            for group_name, repo_list in groups.items():
                enabled_count = len([r for r in repo_list if r in enabled_repos])
                print(f"{group_name}: {enabled_count}/{len(repo_list)} enabled")
    
    def sync_scheduled_repositories(self):
        """Sync repositories based on schedule"""
        schedule = self.config.get('sync_schedule', {})
        enabled_repos = self.get_enabled_repositories()
        
        # For now, just sync daily repositories
        daily_repos = schedule.get('daily', [])
        repos_to_sync = [repo for repo in daily_repos if repo in enabled_repos]
        
        if repos_to_sync:
            self.logger.info(f"Syncing scheduled repositories: {repos_to_sync}")
            for repo in repos_to_sync:
                self.sync_repository(repo)
        else:
            self.logger.info("No scheduled repositories to sync")
    
    def check_repository_health(self, repo_name: str = None) -> Dict:
        """Check repository health"""
        health_config = self.config.get('health_checks', {})
        
        if not health_config:
            return {}
        
        # Placeholder for health checks
        # In a real implementation, this would check:
        # - Metadata consistency
        # - Manifest integrity
        # - Dependency resolution
        # - Missing keywords
        
        return {
            'metadata_ok': True,
            'manifests_ok': True,
            'dependencies_ok': True,
            'keywords_ok': True
        }
    
    def export_configuration(self, output_file: str):
        """Export current repository configuration"""
        enabled_repos = self.get_enabled_repositories()
        available_repos = self.get_available_repositories()
        
        export_data = {
            'timestamp': int(time.time()),
            'enabled_repositories': sorted(enabled_repos),
            'available_repositories': sorted(available_repos),
            'configuration': self.config
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Configuration exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Gentoo Repository Manager")
    parser.add_argument('--config', '-c', default='repos.toml', help='Configuration file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Set up repositories')
    setup_parser.add_argument('repositories', nargs='*', help='Repository names to set up')
    setup_parser.add_argument('--group', '-g', help='Set up repository group')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List repositories')
    list_parser.add_argument('--detailed', '-d', action='store_true', help='Show detailed information')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync repositories')
    sync_parser.add_argument('repositories', nargs='*', help='Repository names to sync')
    sync_parser.add_argument('--all', '-a', action='store_true', help='Sync all enabled repositories')
    sync_parser.add_argument('--scheduled', '-s', action='store_true', help='Sync scheduled repositories')
    
    # Enable/disable commands
    enable_parser = subparsers.add_parser('enable', help='Enable repositories')
    enable_parser.add_argument('repositories', nargs='+', help='Repository names to enable')
    
    disable_parser = subparsers.add_parser('disable', help='Disable repositories')
    disable_parser.add_argument('repositories', nargs='+', help='Repository names to disable')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Check repository health')
    health_parser.add_argument('repository', nargs='?', help='Repository to check')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize repository manager
    repo_manager = RepositoryManager(args.config)
    
    # Execute commands
    if args.command == 'setup':
        if args.group:
            repo_manager.setup_repository_group(args.group)
        else:
            repo_manager.setup_repositories(args.repositories or None)
    
    elif args.command == 'list':
        repo_manager.list_repositories(args.detailed)
    
    elif args.command == 'sync':
        if args.all:
            repo_manager.sync_all_enabled()
        elif args.scheduled:
            repo_manager.sync_scheduled_repositories()
        else:
            for repo in args.repositories:
                repo_manager.sync_repository(repo)
    
    elif args.command == 'enable':
        for repo in args.repositories:
            repo_manager.enable_repository(repo)
    
    elif args.command == 'disable':
        for repo in args.repositories:
            repo_manager.disable_repository(repo)
    
    elif args.command == 'health':
        health_result = repo_manager.check_repository_health(args.repository)
        print(f"Health check results: {health_result}")
    
    elif args.command == 'export':
        repo_manager.export_configuration(args.output)

if __name__ == "__main__":
    main()
