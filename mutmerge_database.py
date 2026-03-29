import sqlite3

class MutMergeDB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS builds (
                id INTEGER PRIMARY KEY,
                package TEXT,
                arch TEXT,
                status TEXT,
                duration INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def get_package_weight(self, package, arch):
        """Returns average build time. Lower = Faster = Higher Priority."""
        cursor = self.conn.execute(
            "SELECT AVG(duration) FROM builds WHERE package=? AND arch=? AND status='SUCCESS'",
            (package, arch)
        )
        row = cursor.fetchone()
        return row[0] if row[0] is not None else 0

    def record_build(self, package, arch, status, duration):
        self.conn.execute(
            "INSERT INTO builds (package, arch, status, duration) VALUES (?, ?, ?, ?)",
            (package, arch, status, duration)
        )
        self.conn.commit()
        """)
        
        # Create skip_combinations table for known bad combos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skip_combinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package TEXT NOT NULL,
                use_flags TEXT NOT NULL,
                reason TEXT,
                timestamp INTEGER NOT NULL
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_package_use ON builds(package, use_flags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skip_package_use ON skip_combinations(package, use_flags)")
        
        conn.commit()
        conn.close()
    
    def should_skip_combination(self, package: str, use_flags: str) -> bool:
        """Check if this USE flag combination should be skipped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM skip_combinations WHERE package = ? AND use_flags = ?",
            (package, use_flags)
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def add_skip_combination(self, package: str, use_flags: str, reason: str):
        """Add a USE flag combination to skip list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO skip_combinations (package, use_flags, reason, timestamp) VALUES (?, ?, ?, ?)",
            (package, use_flags, reason, int(time.time()))
        )
        conn.commit()
        conn.close()
    
    def record_build(self, package: str, use_flags: str, status: str, 
                     build_time: Optional[float] = None, error_log: Optional[str] = None, 
                     binary_path: Optional[str] = None, chroot_env: Optional[str] = None):
        """Record build result in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO builds (package, use_flags, status, timestamp, build_time, error_log, binary_path, chroot_env) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (package, use_flags, status, int(time.time()), build_time, error_log, binary_path, chroot_env)
        )
        conn.commit()
        conn.close()
    
    def get_build_stats(self, package: Optional[str] = None) -> Dict:
        """Get build statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if package:
            cursor.execute("SELECT status, COUNT(*) FROM builds WHERE package = ? GROUP BY status", (package,))
        else:
            cursor.execute("SELECT status, COUNT(*) FROM builds GROUP BY status")
        
        stats = dict(cursor.fetchall())
        conn.close()
        return stats
    
    def get_recent_builds(self, package: Optional[str] = None, limit: int = 10) -> list:
        """Get recent builds for debugging/monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if package:
            cursor.execute(
                "SELECT package, use_flags, status, timestamp, build_time FROM builds WHERE package = ? ORDER BY timestamp DESC LIMIT ?",
                (package, limit)
            )
        else:
            cursor.execute(
                "SELECT package, use_flags, status, timestamp, build_time FROM builds ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        results = cursor.fetchall()
        conn.close()
        return results
