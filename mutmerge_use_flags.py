#!/usr/bin/env python3
"""
USE flag generation and management module for MutMerge
Handles generating combinations of USE flags for testing
"""

import itertools
from typing import List, Set


class USEFlagGenerator:
    """Generate USE flag combinations for testing"""
    
    def __init__(self, base_flags: Set[str], test_flags: List[str], 
                 max_combinations: int = 100):
        self.base_flags = base_flags
        self.test_flags = test_flags
        self.max_combinations = max_combinations
    
    def generate_combinations(self) -> List[Set[str]]:
        """Generate USE flag combinations"""
        combinations = []
        
        # Always include base configuration
        combinations.append(self.base_flags.copy())
        
        # Generate combinations of test flags
        for r in range(1, min(len(self.test_flags) + 1, 6)):  # Limit to avoid explosion
            for combo in itertools.combinations(self.test_flags, r):
                use_set = self.base_flags.copy()
                for flag in combo:
                    if flag.startswith('-'):
                        use_set.discard(flag[1:])
                    else:
                        use_set.add(flag)
                
                combinations.append(use_set)
                
                if len(combinations) >= self.max_combinations:
                    break
            
            if len(combinations) >= self.max_combinations:
                break
        
        return combinations[:self.max_combinations]
    
    def generate_systematic_combinations(self) -> List[Set[str]]:
        """Generate more systematic combinations with better coverage"""
        combinations = []
        
        # Base configuration
        combinations.append(self.base_flags.copy())
        
        # Single flag additions/removals
        for flag in self.test_flags:
            use_set = self.base_flags.copy()
            if flag.startswith('-'):
                use_set.discard(flag[1:])
            else:
                use_set.add(flag)
            combinations.append(use_set)
        
        # Pairwise combinations (important for interaction testing)
        positive_flags = [f for f in self.test_flags if not f.startswith('-')]
        negative_flags = [f[1:] for f in self.test_flags if f.startswith('-')]
        
        for flag1, flag2 in itertools.combinations(positive_flags, 2):
            use_set = self.base_flags.copy()
            use_set.add(flag1)
            use_set.add(flag2)
            combinations.append(use_set)
            
            if len(combinations) >= self.max_combinations:
                break
        
        return combinations[:self.max_combinations]
    
    def validate_flag_combination(self, flags: Set[str]) -> bool:
        """Validate that a flag combination makes sense"""
        # Check for obvious conflicts
        conflicting_pairs = [
            ('debug', 'optimize'),
            ('static', 'shared'),
            ('minimal', 'full'),
        ]
        
        for flag1, flag2 in conflicting_pairs:
            if flag1 in flags and flag2 in flags:
                return False
        
        return True
    
    def filter_valid_combinations(self, combinations: List[Set[str]]) -> List[Set[str]]:
        """Filter out invalid flag combinations"""
        return [combo for combo in combinations if self.validate_flag_combination(combo)]


class USEFlagParser:
    """Parse and normalize USE flags from various sources"""
    
    @staticmethod
    def parse_emerge_output(emerge_output: str) -> Set[str]:
        """Parse USE flags from emerge --pretend output"""
        use_flags = set()
        for line in emerge_output.split('\n'):
            if 'USE=' in line:
                use_part = line.split('USE=')[1].split()[0].strip('"')
                for flag in use_part.split():
                    if flag.startswith('-'):
                        continue  # Skip disabled flags for base set
                    use_flags.add(flag)
        return use_flags
    
    @staticmethod
    def parse_use_string(use_string: str) -> Set[str]:
        """Parse a USE flag string into a set"""
        flags = set()
        for flag in use_string.split():
            flag = flag.strip()
            if flag and not flag.startswith('-'):
                flags.add(flag)
        return flags
    
    @staticmethod
    def format_use_flags(flags: Set[str]) -> str:
        """Format USE flags for emerge command"""
        return ' '.join(sorted(flags))
