"""
Skill Normalizer Service
========================

Handles normalization of skill variants to canonical names.
Examples:
- "py" → "Python"
- "reactjs" → "React"
- "k8s" → "Kubernetes"

Also integrates with your skills.json for domain-specific normalization.
"""

import json
from pathlib import Path
from difflib import SequenceMatcher


class SkillNormalizer:
    def __init__(self):
        """
        Initialize normalizer with normalization maps
        """
        self.data_dir = Path(__file__).parent.parent / "data"

        # Load normalization map (from training package)
        self.normalization_map = self._load_normalization_map()

        # Load skills.json for additional aliases
        self.skills_aliases = self._load_skills_aliases()

        # Combine both sources
        self.combined_map = {**self.normalization_map, **self.skills_aliases}

        print(f"✅ SkillNormalizer initialized with {len(self.combined_map)} mappings")

    def _load_normalization_map(self):
        """Load normalization_map.json from training package"""
        norm_file = self.data_dir / "normalization_map.json"

        if norm_file.exists():
            with open(norm_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"⚠️  Warning: {norm_file} not found. Using empty map.")
            return {}

    def _load_skills_aliases(self):
        """Load aliases from skills.json"""
        skills_file = self.data_dir / "skills.json"
        alias_map = {}

        if skills_file.exists():
            with open(skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                for skill in data.get('skills', []):
                    canonical = skill['name']

                    # Add canonical name mapping (case-insensitive)
                    alias_map[canonical.lower()] = canonical

                    # Add all aliases
                    for alias in skill.get('aliases', []):
                        alias_map[alias.lower()] = canonical

        return alias_map

    def normalize(self, skill_name):
        """
        Normalize a skill name to its canonical form

        Args:
            skill_name (str): Skill name to normalize

        Returns:
            str: Canonical skill name

        Examples:
            normalize("py") → "Python"
            normalize("reactjs") → "React"
            normalize("k8s") → "Kubernetes"
        """
        if not skill_name:
            return skill_name

        # Try exact match (case-insensitive)
        skill_lower = skill_name.lower()
        if skill_lower in self.combined_map:
            return self.combined_map[skill_lower]

        # Try fuzzy match for typos
        canonical = self._fuzzy_match(skill_name)
        if canonical:
            return canonical

        # Return original if no match found
        return skill_name

    def normalize_list(self, skill_names):
        """
        Normalize a list of skill names

        Args:
            skill_names (list): List of skill names

        Returns:
            list: List of canonical skill names (deduplicated)
        """
        if not skill_names:
            return []

        normalized = []
        seen = set()

        for skill in skill_names:
            canonical = self.normalize(skill)
            canonical_lower = canonical.lower()

            # Avoid duplicates
            if canonical_lower not in seen:
                normalized.append(canonical)
                seen.add(canonical_lower)

        return normalized

    def _fuzzy_match(self, skill_name, threshold=0.85):
        """
        Find best fuzzy match for typos

        Args:
            skill_name (str): Skill name with potential typo
            threshold (float): Similarity threshold (0-1)

        Returns:
            str or None: Canonical name if match found, else None
        """
        skill_lower = skill_name.lower()
        best_match = None
        best_score = threshold

        # Get all canonical names (unique values)
        canonical_names = set(self.combined_map.values())

        for canonical in canonical_names:
            # Calculate similarity
            similarity = SequenceMatcher(None, skill_lower, canonical.lower()).ratio()

            if similarity > best_score:
                best_score = similarity
                best_match = canonical

        return best_match

    def get_variants(self, canonical_name):
        """
        Get all known variants of a canonical skill name

        Args:
            canonical_name (str): Canonical skill name

        Returns:
            list: All known variants (including canonical)
        """
        variants = [canonical_name]
        canonical_lower = canonical_name.lower()

        for alias, canonical in self.combined_map.items():
            if canonical.lower() == canonical_lower:
                variants.append(alias)

        return list(set(variants))

    def is_valid_skill(self, skill_name):
        """
        Check if a skill name is known (exact or fuzzy match)

        Args:
            skill_name (str): Skill name to check

        Returns:
            bool: True if skill is known
        """
        skill_lower = skill_name.lower()

        # Check exact match
        if skill_lower in self.combined_map:
            return True

        # Check fuzzy match
        if self._fuzzy_match(skill_name):
            return True

        return False

    def get_all_canonical_names(self):
        """
        Get all canonical skill names

        Returns:
            list: Sorted list of all canonical skill names
        """
        canonical_names = set(self.combined_map.values())
        return sorted(canonical_names)

    def get_stats(self):
        """
        Get statistics about normalization mappings

        Returns:
            dict: Statistics
        """
        canonical_names = set(self.combined_map.values())

        return {
            'total_mappings': len(self.combined_map),
            'canonical_skills': len(canonical_names),
            'average_variants_per_skill': round(len(self.combined_map) / len(canonical_names), 1)
        }


# ============================================================================
# TEST FUNCTION
# ============================================================================

def test_normalizer():
    """Test the normalizer with various inputs"""
    normalizer = SkillNormalizer()

    print("\n" + "=" * 80)
    print("SKILL NORMALIZER TEST")
    print("=" * 80)

    test_cases = [
        # Abbreviations
        ("py", "Python"),
        ("js", "JavaScript"),
        ("k8s", "Kubernetes"),
        ("tf", "Terraform"),

        # Typos
        ("phyton", "Python"),
        ("reactjs", "React"),
        ("javascrpit", "JavaScript"),

        # Case variations
        ("PYTHON", "Python"),
        ("python", "Python"),
        ("pYthon", "Python"),

        # Already canonical
        ("Python", "Python"),
        ("AWS", "AWS"),
    ]

    print("\nNormalization Tests:")
    print("-" * 80)

    for input_skill, expected in test_cases:
        result = normalizer.normalize(input_skill)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_skill}' → '{result}' (expected: '{expected}')")

    # Test list normalization
    print("\n" + "-" * 80)
    print("\nList Normalization Test:")

    test_list = ["py", "Python", "PYTHON", "js", "reactjs", "React"]
    normalized = normalizer.normalize_list(test_list)

    print(f"Input:  {test_list}")
    print(f"Output: {normalized}")
    print(f"(Deduplicated: {len(test_list)} → {len(normalized)})")

    # Show statistics
    print("\n" + "-" * 80)
    print("\nStatistics:")
    stats = normalizer.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_normalizer()
