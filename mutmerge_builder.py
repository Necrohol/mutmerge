#!/usr/bin/env python3
import subprocess
import os
import time

class MutMergeBuilder:
    """
    The Muscle: Executes Gentoo mutations inside Alpine Podman containers.
    Uses 'binary-gentoo' to bridge the gap.
    """
    def __init__(self, image="alpine:latest"):
        self.image = image
        # Identify host to see if we need QEMU binfmt helpers
        self.host_arch = subprocess.check_output(["uname", "-m"]).decode().strip()

    def _get_podman_cmd(self, package, arch, use_flags):
        """Constructs the Podman command to run binary-gentoo."""
        # Mapping for QEMU if cross-compiling
        qemu_map = {"riscv64": "riscv64", "arm64": "aarch64"}
        qemu_arch = qemu_map.get(arch, "")

        cmd = [
            "podman", "run", "--rm",
            "-v", "/var/db/repos:/var/db/repos:ro",     # Mount the DNA (Portage Tree)
            "-v", f"/srv/binhosts/{arch}:/var/cache/binpkgs", # The Showroom
            "-e", f"USE={use_flags}",
            "-e", f"ARCH={arch}",
            "-e", f"QEMU_USER_TARGETS={qemu_arch}" if qemu_arch else "",
            self.image,
            "bash", "-c", f"apk add --no-cache bash python3 py3-pip && pip install binary-gentoo && binary-gentoo emerge --buildpkgonly {package}"
        ]
        return [c for c in cmd if c] # Filter empty strings

    def run_build(self, package, arch, use_flags):
        """
        Runs the build and returns (STATUS, DURATION).
        This is the heartbeat of the 'Ladder' logic.
        """
        print(f"🦾 Muscle: Initializing Podman for {package} ({arch})...")
        
        start_time = time.time()
        cmd = self._get_podman_cmd(package, arch, use_flags)

        try:
            # Execute the Podman container
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            duration = int(time.time() - start_time)
            return "SUCCESS", duration

        except subprocess.CalledProcessError as e:
            duration = int(time.time() - start_time)
            print(f"❌ Muscle: Mutation failed for {package}. Inviable DNA.")
            
            # Save logs for Woodpecker-CI artifacts
            log_name = f"fail_{package.replace('/', '_')}_{arch}.log"
            with open(log_name, "w") as f:
                f.write(e.stderr)
            
            return "FAILED", duration

    def ensure_storage(self, arch):
        """Ensures the binhost directory exists on the host."""
        path = f"/srv/binhosts/{arch}"
        os.makedirs(path, exist_ok=True)
        return path
