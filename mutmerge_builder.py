#!/usr/bin/env python3
"""
Package building module for MutMerge
Handles the actual emerge/build process with various backends
Integrates with binary-gentoo tools for better Docker isolation
"""

import os
import subprocess
import time
import logging
import json
import tempfile
from pathlib import Path
from typing import Set, Tuple, Optional, Dict, List


class PackageBuilder:
    """Handles building packages with different USE flag combinations"""
    
    def __init__(self, chroot_path: Optional[str] = None, use_docker: bool = False,
                 use_binary_gentoo: bool = True, binary_gentoo_config: Optional[str] = None):
        self.chroot_path = chroot_path
        self.use_docker = use_docker
        self.use_binary_gentoo = use_binary_gentoo and self._check_binary_gentoo()
        self.binary_gentoo_config = binary_gentoo_config
        self.logger = logging.getLogger(__name__)
        
        # Initialize binary-gentoo queue if available
        self.build_queue = None
        if self.use_binary_gentoo:
            self._init_binary_gentoo_queue()
    
    def _check_binary_gentoo(self) -> bool:
        """Check if binary-gentoo tools are available"""
        required_tools = ['gentoo-build', 'gentoo-local-queue', 'gentoo-clean']
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '--help'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.logger.warning(f"binary-gentoo tool '{tool}' not found, falling back to basic Docker")
                return False
        
        self.logger.info("binary-gentoo tools detected and available")
        return True
    
    def _init_binary_gentoo_queue(self):
        """Initialize binary-gentoo local queue system"""
        try:
            self.build_queue = "mutmerge_builds"  # Queue name
            # Initialize queue if it doesn't exist
            subprocess.run(['gentoo-local-queue', 'init', self.build_queue], 
                         capture_output=True, check=False)
            self.logger.info(f"Initialized binary-gentoo queue: {self.build_queue}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize binary-gentoo queue: {e}")
            self.build_queue = None
        """Get current USE flags for a package"""
        try:
            result = subprocess.run(
                ['emerge', '--pretend', '--verbose', package],
                capture_output=True, text=True, check=True
            )
            
            # Parse USE flags from emerge output
            from .use_flags import USEFlagParser
            return USEFlagParser.parse_emerge_output(result.stdout)
            
        except subprocess.CalledProcessError:
            return set()
    
    def build_package_variant(self, package: str, use_flags: Set[str], 
                            build_only: bool = True) -> Tuple[bool, str, float]:
        """Build a single package variant using the best available method"""
        if self.use_binary_gentoo:
            return self._build_with_binary_gentoo(package, use_flags, build_only)
        elif self.use_docker:
            return self._build_with_docker(package, use_flags, build_only)
        elif self.chroot_path:
            return self._build_with_chroot(package, use_flags, build_only)
        else:
            return self._build_with_emerge(package, use_flags, build_only)
    
    def _build_with_binary_gentoo(self, package: str, use_flags: Set[str], 
                                  build_only: bool) -> Tuple[bool, str, float]:
        """Build package using binary-gentoo tools with Docker isolation"""
        from .use_flags import USEFlagParser
        use_string = USEFlagParser.format_use_flags(use_flags)
        start_time = time.time()
        
        # Create temporary environment file for USE flags
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_file.write(f'USE="{use_string}"\n')
            env_file.write('FEATURES="binpkg-multi-instance"\n')
            env_file_path = env_file.name
        
        try:
            self.logger.info(f"Building {package} with binary-gentoo, USE={use_string}")
            
            cmd = ['gentoo-build']
            
            # Add build options
            if build_only:
                cmd.extend(['--buildpkg-only'])
            else:
                cmd.extend(['--buildpkg'])
            
            # Add environment file
            cmd.extend(['--env-file', env_file_path])
            
            # Add verbose output
            cmd.extend(['--verbose'])
            
            # Add package
            cmd.append(package)
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600
            )
            
            build_time = time.time() - start_time
            
            if result.returncode == 0:
                return True, "", build_time
            else:
                return False, result.stderr, build_time
        
        except subprocess.TimeoutExpired:
            return False, "Build timeout", time.time() - start_time
        except Exception as e:
            return False, str(e), time.time() - start_time
        finally:
            # Clean up temporary environment file
            try:
                os.unlink(env_file_path)
            except OSError:
                pass
    
    def _build_with_docker(self, package: str, use_flags: Set[str], 
                          build_only: bool) -> Tuple[bool, str, float]:
        """Build package using basic Docker (fallback method)"""
        from .use_flags import USEFlagParser
        use_string = USEFlagParser.format_use_flags(use_flags)
        start_time = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env['USE'] = use_string
        env['FEATURES'] = env.get('FEATURES', '') + ' binpkg-multi-instance'
        
        # Build emerge command
        emerge_cmd = self._build_docker_emerge_command(package, build_only)
        
        try:
            self.logger.info(f"Building {package} with Docker, USE={use_string}")
            result = subprocess.run(
                emerge_cmd, env=env, capture_output=True, text=True, 
                timeout=3600  # 1 hour timeout
            )
            
            build_time = time.time() - start_time
            
            if result.returncode == 0:
                return True, "", build_time
            else:
                return False, result.stderr, build_time
        
        except subprocess.TimeoutExpired:
            return False, "Build timeout", time.time() - start_time
        except Exception as e:
            return False, str(e), time.time() - start_time
    
    def _build_with_chroot(self, package: str, use_flags: Set[str], 
                          build_only: bool) -> Tuple[bool, str, float]:
        """Build package using chroot environment"""
        from .use_flags import USEFlagParser
        use_string = USEFlagParser.format_use_flags(use_flags)
        start_time = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env['USE'] = use_string
        env['FEATURES'] = env.get('FEATURES', '') + ' binpkg-multi-instance'
        
        # Build emerge command
        emerge_cmd = ['chroot', self.chroot_path, 'emerge']
        if build_only:
            emerge_cmd.append('--buildpkgonly')
        else:
            emerge_cmd.append('--buildpkg')
        emerge_cmd.extend(['--verbose', '--tree', package])
        
        try:
            self.logger.info(f"Building {package} with chroot, USE={use_string}")
            result = subprocess.run(
                emerge_cmd, env=env, capture_output=True, text=True, 
                timeout=3600
            )
            
            build_time = time.time() - start_time
            
            if result.returncode == 0:
                return True, "", build_time
            else:
                return False, result.stderr, build_time
        
        except subprocess.TimeoutExpired:
            return False, "Build timeout", time.time() - start_time
        except Exception as e:
            return False, str(e), time.time() - start_time
    
    def _build_with_emerge(self, package: str, use_flags: Set[str], 
                          build_only: bool) -> Tuple[bool, str, float]:
        """Build package using direct emerge (host system)"""
    
        from .use_flags import USEFlagParser
        use_string = USEFlagParser.format_use_flags(use_flags)
        start_time = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env['USE'] = use_string
        env['FEATURES'] = env.get('FEATURES', '') + ' binpkg-multi-instance'
        
        # Build emerge command
        emerge_cmd = ['emerge']
        if build_only:
            emerge_cmd.append('--buildpkgonly')
        else:
            emerge_cmd.append('--buildpkg')
        emerge_cmd.extend(['--verbose', '--tree', package])
        
        try:
            self.logger.info(f"Building {package} with emerge (host), USE={use_string}")
            result = subprocess.run(
                emerge_cmd, env=env, capture_output=True, text=True, 
                timeout=3600
            )
            
            build_time = time.time() - start_time
            
            if result.returncode == 0:
                return True, "", build_time
            else:
                return False, result.stderr, build_time
        
        except subprocess.TimeoutExpired:
            return False, "Build timeout", time.time() - start_time
        except Exception as e:
            return False, str(e), time.time() - start_time
        """Build the emerge command based on configuration"""
        emerge_cmd = ['emerge']
        
        if build_only:
            emerge_cmd.append('--buildpkgonly')
        else:
            emerge_cmd.append('--buildpkg')
        
        emerge_cmd.extend(['--verbose', '--tree', package])
        
        # Execute in chroot or docker if specified
        if self.chroot_path:
            emerge_cmd = ['chroot', self.chroot_path] + emerge_cmd
        elif self.use_docker:
            emerge_cmd = self._build_docker_command(emerge_cmd)
        
        return emerge_cmd
    
    def _build_docker_command(self, emerge_cmd: list) -> list:
        """Build Docker command for isolated builds"""
        docker_cmd = [
            'docker', 'run', '--rm',
            '-v', '/var/db/repos/gentoo:/var/db/repos/gentoo:ro',
            '-v', '/var/cache/distfiles:/var/cache/distfiles',
            '-v', '/var/cache/binpkgs:/var/cache/binpkgs',
            'gentoo/portage'
        ]
        return docker_cmd + emerge_cmd
    
    def test_build_environment(self) -> bool:
        """Test if the build environment is working"""
        if self.use_binary_gentoo:
            return self._test_binary_gentoo_environment()
        elif self.chroot_path:
            return self._test_chroot_environment()
        elif self.use_docker:
            return self._test_docker_environment()
        else:
            return self._test_emerge_environment()
    
    def _test_binary_gentoo_environment(self) -> bool:
        """Test binary-gentoo environment"""
        try:
            result = subprocess.run(
                ['gentoo-build', '--version'],
                capture_output=True, text=True, check=True
            )
            self.logger.info("binary-gentoo environment test successful")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("binary-gentoo environment test failed")
            return False
    
    def _test_chroot_environment(self) -> bool:
        """Test chroot environment"""
        try:
            result = subprocess.run(
                ['chroot', self.chroot_path, 'emerge', '--version'],
                capture_output=True, text=True, check=True
            )
            self.logger.info("Chroot environment test successful")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("Chroot environment test failed")
            return False
    
    def _test_docker_environment(self) -> bool:
        """Test Docker environment"""
        try:
            result = subprocess.run(
                ['docker', 'run', '--rm', 'gentoo/portage', 'emerge', '--version'],
                capture_output=True, text=True, check=True
            )
            self.logger.info("Docker environment test successful")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("Docker environment test failed")
            return False
    
    def _test_emerge_environment(self) -> bool:
        """Test direct emerge environment"""
        try:
            result = subprocess.run(
                ['emerge', '--version'],
                capture_output=True, text=True, check=True
            )
            self.logger.info("Emerge environment test successful")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("Emerge environment test failed")
            return False
    
    def cleanup_build_artifacts(self, package: str):
        """Clean up build artifacts after testing"""
        if self.use_binary_gentoo:
            self._cleanup_with_binary_gentoo(package)
        else:
            self._cleanup_with_emerge(package)
    
    def _cleanup_with_binary_gentoo(self, package: str):
        """Clean up using binary-gentoo tools"""
        try:
            # Use gentoo-clean for proper cleanup
            subprocess.run(['gentoo-clean', '--packages', package], 
                         capture_output=True, check=False)
            self.logger.info(f"Cleaned up {package} with binary-gentoo")
        except Exception as e:
            self.logger.warning(f"Failed to clean up {package} with binary-gentoo: {e}")
    
    def _cleanup_with_emerge(self, package: str):
        """Clean up using emerge"""
        try:
            # Clean temporary build files
            subprocess.run(['emerge', '--clean', package], 
                         capture_output=True, check=False)
            self.logger.info(f"Cleaned up {package} with emerge")
        except Exception as e:
            self.logger.warning(f"Failed to clean up {package}: {e}")
    
    def queue_build_task(self, package: str, use_flags: Set[str]) -> bool:
        """Queue a build task for later processing (binary-gentoo only)"""
        if not self.use_binary_gentoo or not self.build_queue:
            return False
        
        from .use_flags import USEFlagParser
        use_string = USEFlagParser.format_use_flags(use_flags)
        
        try:
            # Create task data
            task_data = {
                'package': package,
                'use_flags': use_string,
                'timestamp': time.time()
            }
            
            # Write task to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as task_file:
                json.dump(task_data, task_file)
                task_file_path = task_file.name
            
            # Push to queue
            result = subprocess.run([
                'gentoo-local-queue', 'push', self.build_queue, task_file_path
            ], capture_output=True, check=True)
            
            # Clean up temporary file
            os.unlink(task_file_path)
            
            self.logger.info(f"Queued build task for {package} with USE={use_string}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to queue build task: {e}")
            return False
    
    def process_queued_builds(self) -> List[Tuple[str, str, bool, str, float]]:
        """Process all queued build tasks (binary-gentoo only)"""
        if not self.use_binary_gentoo or not self.build_queue:
            return []
        
        results = []
        
        try:
            # Get queue status
            result = subprocess.run([
                'gentoo-local-queue', 'status', self.build_queue
            ], capture_output=True, text=True, check=True)
            
            # Process tasks while queue has items
            while 'empty' not in result.stdout.lower():
                # Pop task from queue
                pop_result = subprocess.run([
                    'gentoo-local-queue', 'pop', self.build_queue
                ], capture_output=True, text=True, check=True)
                
                if pop_result.stdout.strip():
                    task_file = pop_result.stdout.strip()
                    
                    # Load task data
                    with open(task_file, 'r') as f:
                        task_data = json.load(f)
                    
                    package = task_data['package']
                    use_string = task_data['use_flags']
                    
                    # Convert USE string back to set
                    from .use_flags import USEFlagParser
                    use_flags = USEFlagParser.parse_use_string(use_string)
                    
                    # Build the package
                    success, error_log, build_time = self._build_with_binary_gentoo(
                        package, use_flags, True
                    )
                    
                    results.append((package, use_string, success, error_log, build_time))
                    
                    # Clean up task file
                    os.unlink(task_file)
                
                # Check queue status again
                result = subprocess.run([
                    'gentoo-local-queue', 'status', self.build_queue
                ], capture_output=True, text=True, check=True)
        
        except Exception as e:
            self.logger.error(f"Error processing queued builds: {e}")
        
        return results
    
    def sync_gentoo_tree(self) -> bool:
        """Sync Gentoo tree using binary-gentoo tools if available"""
        if not self.use_binary_gentoo:
            return False
        
        try:
            result = subprocess.run([
                'gentoo-tree-sync', '/var/db/repos/gentoo'
            ], capture_output=True, text=True, check=True)
            
            self.logger.info("Gentoo tree sync completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to sync Gentoo tree: {e}")
            return False


class BuildResult:
    """Represents the result of a package build"""
    
    def __init__(self, package: str, use_flags: str, success: bool, 
                 build_time: float, error_log: str = ""):
        self.package = package
        self.use_flags = use_flags
        self.success = success
        self.build_time = build_time
        self.error_log = error_log
        self.timestamp = time.time()
    
    def is_dependency_error(self) -> bool:
        """Check if the error is related to dependencies"""
        error_keywords = ["dependency", "conflict", "blocked", "circular"]
        return any(keyword in self.error_log.lower() for keyword in error_keywords)
    
    def is_compilation_error(self) -> bool:
        """Check if the error is a compilation failure"""
        error_keywords = ["failed", "error:", "undefined reference", "compilation terminated"]
        return any(keyword in self.error_log.lower() for keyword in error_keywords)
    
    def get_error_category(self) -> str:
        """Categorize the type of error"""
        if self.success:
            return "SUCCESS"
        elif self.is_dependency_error():
            return "DEPENDENCY_ERROR"
        elif self.is_compilation_error():
            return "COMPILATION_ERROR"
        else:
            return "OTHER_ERROR"
