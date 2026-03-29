import os
import subprocess

class RepoManager:
    def __init__(self, base_path="/etc/portage"):
        self.base_path = base_path
        self.repos_conf_path = os.path.join(base_path, "repos.conf")
        self.make_conf_path = os.path.join(base_path, "make.conf")
        os.makedirs(self.repos_conf_path, exist_ok=True)

    def sync_repos_from_toml(self, config_manager):
        """
        Reads the 'repositories' section of packages.toml and 
        generates the Gentoo repos.conf entries.
        """
        repos = config_manager.get_repositories() # Assuming a 'repositories' key in TOML
        
        for name, url in repos.items():
            repo_file = os.path.join(self.repos_conf_path, f"{name}.conf")
            content = f"[{name}]\nlocation = /var/db/repos/{name}\nsync-type = git\nsync-uri = {url}\n"
            
            with open(repo_file, "w") as f:
                f.write(content)
            print(f"📖 Librarian: Indexed repository [{name}]")

    def setup_binary_instance(self, arch):
        """
        Enables binpkg-multi-instance in make.conf so the Squid 
        can store multiple mutations of the same package.
        """
        # We append/update the multi-instance feature
        with open(self.make_conf_path, "a+") as f:
            f.seek(0)
            content = f.read()
            if 'binpkg-multi-instance' not in content:
                f.write('\nFEATURES="${FEATURES} binpkg-multi-instance"\n')
                f.write(f'PKGDIR="/srv/binhosts/{arch}"\n')
        
        print(f"🧬 Librarian: Multi-instance enabled for {arch}")

    def get_ebuild_path(self, package_cp):
        """Returns the physical path of an ebuild for the builder."""
        # Simple wrapper for 'equery which' or manual path finding
        try:
            path = subprocess.check_output(["portageq", "get_repo_path", "/", "gentoo"]).decode().strip()
            return os.path.join(path, package_cp)
        except:
            return None
