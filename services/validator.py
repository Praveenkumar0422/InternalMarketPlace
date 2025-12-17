class ApplicationValidator:
    def __init__(self, db_service=None):
        self.db_service = db_service

    def calculate_query_match(self, employee_data, query_requirements):
        """
        Calculate match percentage based on search query requirements
        NOW USES REAL SQL DATA!

        Args:
            employee_data: Dict with employee info from vector + SQL database
            query_requirements: Parsed query requirements

        Returns:
            Dict with match percentage and detailed breakdown
        """
        scores = {
            'skill_match': 0,
            'experience_match': 0,
            'location_match': 0,
            'availability_match': 0,
            'semantic_similarity': employee_data.get('similarity_score', 0)
        }

        weights = {
            'skill_match': 40,
            'experience_match': 30,
            'location_match': 10,
            'availability_match': 10,
            'semantic_similarity': 10
        }

        total_weight = sum(weights.values())

        # Get REAL employee data from SQL
        emp_info = employee_data.get('employee_data', {})
        emp_skills = employee_data.get('skills', [])  # Real EmployeeSkills data!

        # Build skill lookup with REAL years
        emp_skill_map = {}
        for skill in emp_skills:
            skill_name_lower = skill['skill_name'].lower()
            emp_skill_map[skill_name_lower] = {
                'years': skill['years_of_experience'],
                'level': skill['proficiency_level']
            }

        skill_analysis = []

        # 1. SKILL MATCHING (40%)
        required_skills = query_requirements.get('skills', [])
        if required_skills:
            matched_skills = 0
            for req_skill in required_skills:
                req_skill_lower = req_skill.lower()

                has_skill = req_skill_lower in emp_skill_map

                if has_skill:
                    matched_skills += 1
                    skill_info = emp_skill_map[req_skill_lower]
                    skill_analysis.append({
                        'skill': req_skill,
                        'status': 'Match',
                        'employee_has': True,
                        'employee_years': skill_info['years'],
                        'proficiency': skill_info['level']
                    })
                else:
                    skill_analysis.append({
                        'skill': req_skill,
                        'status': 'Missing',
                        'employee_has': False,
                        'employee_years': 0,
                        'proficiency': None
                    })

            if required_skills:
                scores['skill_match'] = (matched_skills / len(required_skills)) * 100
        else:
            scores['skill_match'] = 100

        # 2. EXPERIENCE MATCHING (30%) - NOW WITH REAL DATA!
        experience_req = query_requirements.get('min_years_experience')
        experience_context = query_requirements.get('experience_context', {})

        if experience_req:
            if experience_context.get('type') == 'skill_specific':
                # Check ACTUAL skill-specific experience from EmployeeSkills table
                target_skill = experience_context.get('skill')

                if target_skill and target_skill.lower() in emp_skill_map:
                    actual_years = emp_skill_map[target_skill.lower()]['years']

                    operator = query_requirements.get('experience_operator', 'gte')
                    meets_requirement = self._check_experience_requirement(
                        actual_years, experience_req, operator
                    )

                    if meets_requirement:
                        scores['experience_match'] = 100
                    else:
                        # Partial credit based on actual years
                        ratio = min(actual_years / experience_req, 1.0) if experience_req > 0 else 0
                        scores['experience_match'] = ratio * 80  # Cap at 80% for partial
                else:
                    # Don't have the specific skill
                    scores['experience_match'] = 0

            elif experience_context.get('type') == 'total':
                # Check ACTUAL total career experience from Employees table
                actual_total_years = emp_info.get('TotalExperience', 0)

                operator = query_requirements.get('experience_operator', 'gte')
                meets_requirement = self._check_experience_requirement(
                    actual_total_years, experience_req, operator
                )

                if meets_requirement:
                    scores['experience_match'] = 100
                else:
                    ratio = min(actual_total_years / experience_req, 1.0) if experience_req > 0 else 0
                    scores['experience_match'] = ratio * 80
        else:
            scores['experience_match'] = 100

        # 3. LOCATION MATCHING (10%)
        required_location = query_requirements.get('location')
        emp_location = emp_info.get('Location', '')

        if required_location:
            if emp_location.lower() == required_location.lower():
                scores['location_match'] = 100
            else:
                scores['location_match'] = 0
        else:
            scores['location_match'] = 100

        # 4. AVAILABILITY MATCHING (10%)
        required_availability = query_requirements.get('availability_status')
        emp_availability = emp_info.get('AvailabilityStatus', '')

        if required_availability:
            if emp_availability.lower() == required_availability.lower():
                scores['availability_match'] = 100
            elif emp_availability.lower() == 'available' and required_availability.lower() == 'limited':
                scores['availability_match'] = 100
            else:
                scores['availability_match'] = 0
        else:
            scores['availability_match'] = 100

        # Calculate weighted average
        total_score = sum(scores[key] * weights[key] / 100 for key in scores.keys())
        overall_percentage = (total_score / total_weight) * 100

        # Build detailed experience analysis
        experience_analysis = {
            'required': experience_req,
            'type': experience_context.get('type') if experience_context else 'total',
            'skill': experience_context.get('skill') if experience_context else None,
            'operator': query_requirements.get('experience_operator', 'gte'),
            'meets_requirement': scores['experience_match'] >= 80
        }

        # Add actual years to analysis
        if experience_context.get('type') == 'skill_specific':
            target_skill = experience_context.get('skill')
            if target_skill and target_skill.lower() in emp_skill_map:
                experience_analysis['actual_years'] = emp_skill_map[target_skill.lower()]['years']
            else:
                experience_analysis['actual_years'] = 0
        elif experience_context.get('type') == 'total':
            experience_analysis['actual_years'] = emp_info.get('TotalExperience', 0)

        return {
            'overall_match_percentage': round(overall_percentage, 1),
            'component_scores': scores,
            'skill_analysis': skill_analysis,
            'experience_analysis': experience_analysis,
            'location_match': scores['location_match'] == 100,
            'availability_match': scores['availability_match'] == 100,
            'weights_used': weights
        }

    def _check_experience_requirement(self, employee_years, required_years, operator):
        """Check if employee experience meets requirement based on operator"""
        if operator == 'gt':
            return employee_years > required_years
        elif operator == 'gte':
            return employee_years >= required_years
        elif operator == 'lt':
            return employee_years < required_years
        elif operator == 'lte':
            return employee_years <= required_years
        elif operator == 'eq':
            return employee_years == required_years
        else:
            return employee_years >= required_years

    def calculate_skill_match(self, employee_skills, requirement_skills):
        """Calculate how well employee skills match requirement"""
        if not requirement_skills:
            return 100, []

        total_weight = sum(skill.get('weightage', 1) for skill in requirement_skills)
        earned_weight = 0
        skill_analysis = []

        # Create lookup for employee skills
        emp_skill_map = {s['skill_name'].lower(): s for s in employee_skills}

        for req_skill in requirement_skills:
            skill_name = req_skill['skill_name'].lower()
            min_years = req_skill.get('min_years_required', 0)
            weightage = req_skill.get('weightage', 1)
            is_mandatory = req_skill.get('is_mandatory', False)

            analysis = {
                'skill_name': req_skill['skill_name'],
                'required_years': min_years,
                'is_mandatory': is_mandatory,
                'status': 'Missing',
                'employee_years': 0,
                'score_contribution': 0
            }

            if skill_name in emp_skill_map:
                emp_skill = emp_skill_map[skill_name]
                emp_years = emp_skill.get('years_of_experience', 0)
                analysis['employee_years'] = emp_years

                if emp_years >= min_years:
                    analysis['status'] = 'Match'
                    analysis['score_contribution'] = weightage
                    earned_weight += weightage
                elif emp_years > 0:
                    # Partial credit
                    partial = (emp_years / min_years) * weightage if min_years > 0 else weightage
                    analysis['status'] = 'Partial'
                    analysis['score_contribution'] = partial
                    earned_weight += partial

            skill_analysis.append(analysis)

        match_percentage = (earned_weight / total_weight * 100) if total_weight > 0 else 0
        return round(match_percentage, 1), skill_analysis

    def get_recommendation(self, match_percentage, skill_analysis):
        """Generate AI recommendation based on match analysis"""
        # Check mandatory skills
        missing_mandatory = [s for s in skill_analysis
                             if s['is_mandatory'] and s['status'] == 'Missing']

        if missing_mandatory:
            return {
                'recommendation': 'Not recommended',
                'reason': f"Missing mandatory skills: {', '.join(s['skill_name'] for s in missing_mandatory)}",
                'suggested_action': 'Consider training or alternative candidates'
            }

        if match_percentage >= 80:
            return {
                'recommendation': 'Good fit',
                'reason': 'Candidate meets or exceeds all major skill requirements',
                'suggested_action': 'Proceed with interview'
            }
        elif match_percentage >= 60:
            partial_skills = [s for s in skill_analysis if s['status'] == 'Partial']
            return {
                'recommendation': 'Needs training',
                'reason': f"Good foundation but needs improvement in: {', '.join(s['skill_name'] for s in partial_skills[:3])}",
                'suggested_action': 'Consider with training plan'
            }
        else:
            missing_skills = [s for s in skill_analysis if s['status'] == 'Missing']
            return {
                'recommendation': 'Not recommended',
                'reason': f"Significant skill gaps: {', '.join(s['skill_name'] for s in missing_skills[:3])}",
                'suggested_action': 'Look for better matched candidates'
            }

    def generate_learning_suggestions(self, skill_analysis):
        """Generate learning suggestions for skill gaps"""
        suggestions = []

        for skill in skill_analysis:
            if skill['status'] in ['Missing', 'Partial']:
                gap = skill['required_years'] - skill['employee_years']

                suggestion = {
                    'skill_name': skill['skill_name'],
                    'current_level': skill['employee_years'],
                    'required_level': skill['required_years'],
                    'gap': gap,
                    'priority': 'High' if skill['is_mandatory'] else 'Medium',
                    'estimated_training_hours': int(gap * 40)  # Rough estimate
                }
                suggestions.append(suggestion)

        # Sort by priority and gap
        suggestions.sort(key=lambda x: (0 if x['priority'] == 'High' else 1, -x['gap']))

        return suggestions

    def validate_application(self, employee_skills, requirement_skills):
        """Main validation method"""
        match_percentage, skill_analysis = self.calculate_skill_match(
            employee_skills, requirement_skills
        )

        recommendation = self.get_recommendation(match_percentage, skill_analysis)
        learning_suggestions = self.generate_learning_suggestions(skill_analysis)

        return {
            'match_percentage': match_percentage,
            'ai_score': match_percentage,
            'ai_recommendation': recommendation['recommendation'],
            'recommendation_details': recommendation,
            'skill_analysis': skill_analysis,
            'learning_suggestions': learning_suggestions
        }
