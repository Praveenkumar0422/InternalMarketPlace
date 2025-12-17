# query_parser.py
# Natural Language Query Parser with SpaCy NER
# VERSION 3.0 - Added category detection and expansion for semantic search

import spacy
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class QueryParser:
    def __init__(self):
        """Initialize the query parser with SpaCy model"""
        self.nlp = None
        self.tech_dict = {}
        self.tech_categories = {}  # ⭐ NEW: Category structure
        self.normalization_map = {}
        self.load_models()
        self.load_tech_dictionary()
        self.load_normalization_map()

    def load_models(self):
        """Load the trained SpaCy NER model"""
        model_path = "./models/talent_ner_model"

        if os.path.exists(model_path):
            print(f"[INFO] Loading SpaCy model from {model_path}")
            try:
                self.nlp = spacy.load(model_path)
                print(f"[INFO] ✅ Model loaded successfully!")
                print(f"[INFO] Entity types: {list(self.nlp.get_pipe('ner').labels)}")
            except Exception as e:
                print(f"[ERROR] ❌ Failed to load model: {e}")
                print(f"[INFO] Using blank English model as fallback")
                self.nlp = spacy.blank("en")
        else:
            print(f"[ERROR] ❌ Trained model not found at {model_path}")
            print(f"[ERROR] Please run: python train_spacy_model.py")
            print(f"[INFO] Using blank English model as fallback")
            self.nlp = spacy.blank("en")

    def load_tech_dictionary(self):
        """Load technology dictionary with categories"""
        dict_path = "./data/tech_dict_with_categories.json"

        if os.path.exists(dict_path):
            try:
                with open(dict_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tech_dict = data
                    # ⭐ NEW: Extract categories structure
                    self.tech_categories = data.get('categories', {})
                print(f"[INFO] ✅ Loaded tech dictionary with {len(self.tech_categories)} categories")
            except Exception as e:
                print(f"[ERROR] Failed to load tech dictionary: {e}")
                self.tech_dict = {}
                self.tech_categories = {}
        else:
            print(f"[WARNING] Tech dictionary not found at {dict_path}")
            self.tech_dict = {}
            self.tech_categories = {}

    def load_normalization_map(self):
        """Load normalization map for skill variants"""
        map_path = "./data/normalization_map.json"

        if os.path.exists(map_path):
            try:
                with open(map_path, 'r', encoding='utf-8') as f:
                    self.normalization_map = json.load(f)
                print(f"[INFO] ✅ Loaded {len(self.normalization_map)} normalization mappings")
            except Exception as e:
                print(f"[ERROR] Failed to load normalization map: {e}")
                self.normalization_map = {}
        else:
            print(f"[WARNING] Normalization map not found at {map_path}")
            self.normalization_map = {}

    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name using normalization map"""
        skill_lower = skill.lower().strip()

        if skill_lower in self.normalization_map:
            return self.normalization_map[skill_lower]

        return skill.strip()
    
    def expand_category(self, category: str) -> List[str]:
        """
        Expand a category to its constituent technologies
        
        ⭐ Uses tech_categories structure from JSON
        """
        category_lower = category.lower().strip()
        expanded_skills = []

        # Check new structure first
        for cat_name, cat_data in self.tech_categories.items():
            if cat_name.lower() == category_lower:
                return cat_data.get('technologies', [])
        
        # Fallback to old structure (if exists)
        for tech, info in self.tech_dict.items():
            if isinstance(info, dict) and 'category' in info:
                tech_category = info.get('category', '').lower()
                if tech_category == category_lower:
                    expanded_skills.append(tech)

        return expanded_skills

    def _extract_skills_from_keywords(self, query_lower: str) -> List[str]:
        """
        Fallback: Extract skills by keyword matching when SpaCy NER misses them
        (e.g., lowercase "angular" instead of "Angular")
        """
        found_skills = []
        
        # Get all known technologies from tech_dict
        known_techs = []
        
        # From categories structure
        for category_data in self.tech_categories.values():
            known_techs.extend(category_data.get('technologies', []))
        
        # Remove duplicates
        known_techs = list(set(known_techs))
        
        # Check if any technology appears in query (case-insensitive)
        for tech in known_techs:
            tech_lower = tech.lower()
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(tech_lower) + r'\b'
            if re.search(pattern, query_lower):
                found_skills.append(tech)
                print(f"[INFO] 🔍 Found skill via keyword match: {tech}")
        
        return found_skills

    def _detect_categories_and_expand(self, query_lower: str, doc) -> Tuple[List[str], List[str]]:
        """
        ⭐ NEW: Detect technology categories in query and expand to specific skills
        
        Args:
            query_lower: Lowercase query string
            doc: SpaCy doc object
            
        Returns:
            tuple: (detected_categories, category_skills)
        """
        detected_categories = []
        category_skills = []
        
        print(f"[DEBUG] Checking for categories in query: {query_lower}")
        
        # Check each category
        for category_name, category_data in self.tech_categories.items():
            category_name_lower = category_name.lower()
            keywords = category_data.get('keywords', [])
            aliases = category_data.get('aliases', [])
            technologies = category_data.get('technologies', [])
            
            # Check if category name is in query
            if category_name_lower in query_lower:
                detected_categories.append(category_name)
                category_skills.extend(technologies)
                print(f"[INFO] 📂 Category detected: {category_name} (from category name)")
                continue
            
            # Check aliases
            for alias in aliases:
                if alias.lower() in query_lower:
                    detected_categories.append(category_name)
                    category_skills.extend(technologies)
                    print(f"[INFO] 📂 Category detected: {category_name} (from alias: '{alias}')")
                    break
            
            if category_name in detected_categories:
                continue
            
            # Check keywords (more lenient matching)
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Only match keywords of 4+ chars to avoid false positives
                if len(keyword_lower) >= 4 and keyword_lower in query_lower:
                    # Additional check: make sure it's a word boundary match
                    # This prevents "cloud" from matching "cloudy"
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    if re.search(pattern, query_lower):
                        detected_categories.append(category_name)
                        category_skills.extend(technologies)
                        print(f"[INFO] 📂 Category detected: {category_name} (from keyword: '{keyword}')")
                        break
        
        # Remove duplicates
        detected_categories = list(dict.fromkeys(detected_categories))  # Preserves order
        category_skills = list(dict.fromkeys(category_skills))
        
        print(f"[INFO] 📊 Categories found: {detected_categories}")
        print(f"[INFO] 📊 Category skills expanded: {len(category_skills)} skills")
        
        return detected_categories, category_skills

    def parse_query(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return self._empty_result()

        query_lower = query.lower()
        doc = self.nlp(query)

        # ⭐ STEP 1: Detect categories
        detected_categories, category_skills = self._detect_categories_and_expand(query_lower, doc)

        # ⭐ STEP 2: Extract entities from SpaCy
        technologies = []
        tech_categories = []
        tech_experiences = []
        overall_experiences = []
        locations = []
        skill_levels = []
        roles = []
        certifications = []
        companies = []
        dates = []

        for ent in doc.ents:
            entity_text = ent.text.strip()

            if ent.label_ == "TECHNOLOGY":
                normalized = self.normalize_skill(entity_text)
                if normalized not in technologies:
                    technologies.append(normalized)

            elif ent.label_ == "TECH_CATEGORY":
                if entity_text.lower() not in [c.lower() for c in tech_categories]:
                    tech_categories.append(entity_text)
                    expanded = self.expand_category(entity_text)
                    category_skills.extend(expanded)

            elif ent.label_ == "TECH_EXPERIENCE":
                tech_experiences.append(entity_text)

            elif ent.label_ == "OVERALL_EXPERIENCE":
                overall_experiences.append(entity_text)

            elif ent.label_ == "GPE":
                if entity_text not in locations:
                    locations.append(entity_text)

            elif ent.label_ == "SKILL_LEVEL":
                if entity_text not in skill_levels:
                    skill_levels.append(entity_text)

            elif ent.label_ == "ROLE":
                if entity_text not in roles:
                    roles.append(entity_text)

            elif ent.label_ == "CERTIFICATION":
                if entity_text not in certifications:
                    certifications.append(entity_text)

            elif ent.label_ == "ORG":
                if entity_text not in companies:
                    companies.append(entity_text)

            elif ent.label_ == "DATE":
                if entity_text not in dates:
                    dates.append(entity_text)

        # ⭐ STEP 2.5: Fallback keyword matching for case-insensitive skills
        keyword_skills = self._extract_skills_from_keywords(query_lower)
        for skill in keyword_skills:
            if skill not in technologies:
                technologies.append(skill)
                print(f"[INFO] ✅ Added skill from keyword match: {skill}")

        # ⭐ STEP 3: Merge categories
        all_categories = list(dict.fromkeys(detected_categories + tech_categories))
        category_skills = list(dict.fromkeys(category_skills))

        # ⭐ STEP 4: Map experiences to specific skills
        skill_experience_map = self._map_experiences_to_skills(
            query,
            technologies,
            tech_experiences,
            overall_experiences
        )

        # Get global experience (for backward compatibility)
        global_min, global_max = self._extract_global_experience(tech_experiences, overall_experiences)
        exp_operator = self._extract_operator(query, tech_experiences, overall_experiences)

        # Determine global experience context
        experience_context = self._determine_experience_context(
            query,
            technologies,
            tech_experiences,
            overall_experiences
        )

        location = locations[0] if locations else None
        availability = self._extract_availability(query)

        # Build parsed result WITH CATEGORIES
        parsed_result = {
            'skills': technologies,
            'categories': all_categories,  # ⭐ Now includes detected categories
            'category_skills': category_skills,  # ⭐ Now includes expanded skills

            # Global experience (backward compatibility)
            'min_years_experience': global_min,
            'max_years_experience': global_max,
            'experience_operator': exp_operator,
            'experience_context': experience_context,

            # Per-skill experience requirements
            'skill_requirements': skill_experience_map,

            'location': location,
            'availability_status': availability,
            'skill_levels': skill_levels,
            'roles': roles,
            'certifications': certifications,
            'companies': companies,
            'dates': dates
        }

        # Build applied filters
        applied_filters = self._build_applied_filters(parsed_result)

        # ⭐ Calculate total skills (explicit + category)
        all_skills = list(dict.fromkeys(technologies + category_skills))

        return {
            'original_query': query,
            'parsed': parsed_result,
            'applied_filters': applied_filters,
            'skills_found': len(all_skills),  # ⭐ Total of explicit + category skills
            'entities_detected': {
                'skills': technologies,
                'categories': all_categories,
                'category_skills': category_skills,
                'tech_experiences': tech_experiences,
                'overall_experiences': overall_experiences,
                'location': location,
                'skill_levels': skill_levels,
                'roles': roles,
                'certifications': certifications,
                'companies': companies,
                'dates': dates
            }
        }

    def _map_experiences_to_skills(
            self,
            query: str,
            skills: List[str],
            tech_experiences: List[str],
            overall_experiences: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Map experience requirements to specific skills

        Example:
        Query: "Python with 2-5 years and AWS with 1 year"
        Returns: [
            {"skill": "Python", "min_years": 2, "max_years": 5, "operator": "between"},
            {"skill": "AWS", "min_years": 1, "max_years": None, "operator": "gte"}
        ]
        """
        skill_requirements = []
        query_lower = query.lower()

        for skill in skills:
            skill_lower = skill.lower()

            # Find experience mentions near this skill
            all_experiences = tech_experiences + overall_experiences

            for exp in all_experiences:
                exp_lower = exp.lower()

                # Check if this experience is associated with this skill
                skill_pos = query_lower.find(skill_lower)
                exp_pos = query_lower.find(exp_lower)

                if skill_pos != -1 and exp_pos != -1:
                    # If skill and experience are within 50 characters of each other
                    if abs(skill_pos - exp_pos) < 50:
                        # Check for connecting words
                        between_text = query_lower[min(skill_pos, exp_pos):max(skill_pos, exp_pos) + len(exp_lower)]

                        # Look for "with", "of", "in" patterns
                        if any(word in between_text for word in ['with', 'of', 'in', 'having']):
                            min_years, max_years = self._extract_year_range(exp)

                            if min_years:
                                operator = 'between' if max_years else 'gte'

                                skill_requirements.append({
                                    'skill': skill,
                                    'min_years': min_years,
                                    'max_years': max_years,
                                    'operator': operator,
                                    'experience_type': 'skill_specific'
                                })
                                break  # Found experience for this skill

        # If no specific mapping found, use global experience for all skills
        if not skill_requirements and (tech_experiences or overall_experiences):
            all_exp = tech_experiences + overall_experiences
            if all_exp:
                min_years, max_years = self._extract_year_range(all_exp[0])
                if min_years:
                    operator = 'between' if max_years else 'gte'
                    for skill in skills:
                        skill_requirements.append({
                            'skill': skill,
                            'min_years': min_years,
                            'max_years': max_years,
                            'operator': operator,
                            'experience_type': 'skill_specific'
                        })

        return skill_requirements

    def _extract_global_experience(self, tech_experiences: List[str], overall_experiences: List[str]) -> Tuple[
        Optional[float], Optional[float]]:
        """Extract global experience (for backward compatibility)"""
        # Use the FIRST experience mentioned
        all_exp = tech_experiences + overall_experiences
        if all_exp:
            return self._extract_year_range(all_exp[0])
        return (None, None)

    def _build_applied_filters(self, parsed_result: Dict) -> List[str]:
        """Build human-readable filter descriptions"""
        filters = []

        if parsed_result['skills']:
            filters.append(f"Skills: {', '.join(parsed_result['skills'])}")

        if parsed_result['categories']:
            filters.append(f"Categories: {', '.join(parsed_result['categories'])}")

        # Show per-skill requirements
        if parsed_result.get('skill_requirements'):
            for req in parsed_result['skill_requirements']:
                skill = req['skill']
                min_years = req['min_years']
                max_years = req.get('max_years')

                if max_years:
                    exp_text = f"{min_years}-{max_years} years"
                else:
                    exp_text = f"{min_years}+ years"

                filters.append(f"{skill}: {exp_text}")
        elif parsed_result['min_years_experience']:
            # Fallback to global experience
            if parsed_result['max_years_experience']:
                exp_text = f"{parsed_result['min_years_experience']}-{parsed_result['max_years_experience']} years"
            else:
                exp_text = f"{parsed_result['min_years_experience']}+ years"

            if parsed_result['experience_context'] and parsed_result['experience_context']['type'] == 'skill_specific':
                exp_text += f" in {parsed_result['experience_context']['skill']}"

            filters.append(f"Experience: {exp_text}")

        if parsed_result['location']:
            filters.append(f"Location: {parsed_result['location']}")

        if parsed_result['availability_status']:
            filters.append(f"Availability: {parsed_result['availability_status']}")

        return filters

    def _extract_year_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract year range from text

        Examples:
        - "2 to 5 years" → (2.0, 5.0)
        - "3-7 years" → (3.0, 7.0)
        - "5 years" → (5.0, None)
        - "5+ years" → (5.0, None)

        Returns: (min_years, max_years) tuple
        """
        # Pattern 1: "X to Y years" or "X-Y years"
        pattern1 = r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:year|yr)'
        match = re.search(pattern1, text.lower())

        if match:
            try:
                min_years = float(match.group(1))
                max_years = float(match.group(2))
                return (min_years, max_years)
            except ValueError:
                pass

        # Pattern 2: Single value "X years" or "X+ years"
        pattern2 = r'(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr)'
        match = re.search(pattern2, text.lower())

        if match:
            try:
                years = float(match.group(1))
                return (years, None)
            except ValueError:
                pass

        return (None, None)

    def _extract_years(self, tech_experiences: List[str], overall_experiences: List[str]) -> Tuple[
        Optional[float], Optional[float]]:
        """Extract numeric years from experience strings

        Returns: (min_years, max_years) tuple
        """
        # Try tech-specific experiences first
        for exp in tech_experiences:
            min_years, max_years = self._extract_year_range(exp)
            if min_years:
                return (min_years, max_years)

        # Fall back to overall experiences
        for exp in overall_experiences:
            min_years, max_years = self._extract_year_range(exp)
            if min_years:
                return (min_years, max_years)

        return (None, None)

    def _extract_operator(self, query: str, tech_experiences: List[str], overall_experiences: List[str]) -> str:
        """Determine experience operator"""
        query_lower = query.lower()
        all_experiences = tech_experiences + overall_experiences

        # Check for range patterns
        for exp in all_experiences:
            if 'to' in exp.lower() or '-' in exp:
                return 'between'  # Range operator

        # Check for explicit operators
        if any(phrase in query_lower for phrase in ['more than', 'greater than', 'over', 'above']):
            return 'gt'
        elif any(phrase in query_lower for phrase in ['at least', 'minimum', 'min']):
            return 'gte'
        elif any(phrase in query_lower for phrase in ['less than', 'under', 'below']):
            return 'lt'
        elif any(phrase in query_lower for phrase in ['at most', 'maximum', 'max']):
            return 'lte'
        elif any(phrase in query_lower for phrase in ['exactly', 'equal to']):
            return 'eq'

        # Check for + symbol
        for exp in all_experiences:
            if '+' in exp:
                return 'gte'

        return 'gte'

    def _determine_experience_context(
            self,
            query: str,
            skills: List[str],
            tech_experiences: List[str],
            overall_experiences: List[str]
    ) -> Optional[Dict[str, str]]:
        """
        Determine if experience is skill-specific or total

        IMPROVED: Better detection of "of Python" patterns
        """
        if not tech_experiences and not overall_experiences:
            return None

        query_lower = query.lower()

        # Check for explicit "of SKILL" or "in SKILL" patterns FIRST
        for skill in skills:
            skill_lower = skill.lower()

            # Pattern: "X years of Python experience"
            if f"of {skill_lower}" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'Explicit "of {skill}" pattern detected'
                }

            # Pattern: "X years in Python"
            if f"in {skill_lower}" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'Explicit "in {skill}" pattern detected'
                }

            # Pattern: "Python experience"
            if f"{skill_lower} experience" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'"{skill} experience" pattern detected'
                }

            # Pattern: "experience with Python"
            if f"with {skill_lower}" in query_lower and "experience" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'"experience with {skill}" pattern detected'
                }

        # If TECH_EXPERIENCE entity detected, it's skill-specific
        if tech_experiences:
            target_skill = skills[0] if skills else None
            return {
                'type': 'skill_specific',
                'skill': target_skill,
                'reason': 'TECH_EXPERIENCE entity detected by SpaCy'
            }

        # If only OVERALL_EXPERIENCE, it's total
        elif overall_experiences:
            return {
                'type': 'total',
                'skill': None,
                'reason': 'OVERALL_EXPERIENCE entity detected, no specific skill mentioned'
            }

        return None

    def _extract_availability(self, query: str) -> Optional[str]:
        """Extract availability status from query"""
        query_lower = query.lower()

        if any(word in query_lower for word in ['available', 'free', 'ready']):
            return 'Available'
        elif any(word in query_lower for word in ['limited', 'partial', 'part-time']):
            return 'Limited'
        elif any(word in query_lower for word in ['not available', 'busy', 'occupied']):
            return 'Not Available'

        return None

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'original_query': '',
            'parsed': {
                'skills': [],
                'categories': [],
                'category_skills': [],
                'min_years_experience': None,
                'max_years_experience': None,
                'experience_operator': 'gte',
                'experience_context': None,
                'skill_requirements': [],
                'location': None,
                'availability_status': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            },
            'applied_filters': [],
            'skills_found': 0,
            'entities_detected': {
                'skills': [],
                'categories': [],
                'category_skills': [],
                'tech_experiences': [],
                'overall_experiences': [],
                'location': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            }
        }

    def get_entity_types(self) -> List[str]:
        """Get list of entity types the model can detect"""
        if self.nlp and 'ner' in self.nlp.pipe_names:
            return list(self.nlp.get_pipe('ner').labels)
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            'model_loaded': self.nlp is not None,
            'entity_types': self.get_entity_types(),
            'tech_dict_size': len(self.tech_dict),
            'tech_categories': len(self.tech_categories),
            'normalization_mappings': len(self.normalization_map)
        }


# Singleton instance
_parser_instance = None


def get_parser() -> QueryParser:
    """Get or create QueryParser singleton instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QueryParser()
    return _parser_instance