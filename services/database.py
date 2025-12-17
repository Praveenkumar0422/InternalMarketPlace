import pyodbc
from config import Config


class DatabaseService:
    def __init__(self):
        """Initialize database connection using existing config"""
        self.connection_string = Config.DB_CONNECTION
        self.connection = None

    def get_connection(self):
        """Get database connection (reuse or create new)"""
        try:
            if self.connection is None or self.connection.closed:
                self.connection = pyodbc.connect(self.connection_string)
            return self.connection
        except Exception as e:
            print(f"Database connection error: {e}")
            raise

    def execute_query(self, query, params=None):
        """Execute SELECT query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Fetch all results
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            return results
        finally:
            cursor.close()

    def get_employee_skills(self, employee_id):
        """
        Get detailed skills for an employee including years of experience

        Returns:
            List of dicts with skill details
        """
        query = """
            SELECT 
                s.SkillId,
                s.SkillName,
                s.Category,
                es.YearsOfExperience,
                es.ProficiencyLevel,
                es.LastUsedDate
            FROM EmployeeSkills es
            INNER JOIN Skills s ON es.SkillId = s.SkillId
            WHERE es.EmployeeId = ?
            ORDER BY es.YearsOfExperience DESC
        """

        return self.execute_query(query, (employee_id,))

    def get_employee_basic_info(self, employee_id):
        """Get basic employee information"""
        query = """
            SELECT 
                e.EmployeeId,
                e.FullName,
                e.Email,
                e.Designation,
                e.Location,
                e.YearsOfExperience as TotalExperience,
                e.AvailabilityStatus,
                t.TeamName,
                t.Department
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.TeamId
            WHERE e.EmployeeId = ?
        """

        results = self.execute_query(query, (employee_id,))
        return results[0] if results else None

    def get_employee_domains(self, employee_id):
        """Get domain/industry experience for employee"""
        query = """
            SELECT 
                d.DomainId,
                d.DomainName,
                d.Category,
                ed.YearsOfExperience,
                ed.ProficiencyLevel
            FROM EmployeeDomains ed
            INNER JOIN Domains d ON ed.DomainId = d.DomainId
            WHERE ed.EmployeeId = ?
        """

        return self.execute_query(query, (employee_id,))

    def get_employees_by_ids(self, employee_ids):
        """
        Get multiple employees' data efficiently (BATCH QUERY)

        Args:
            employee_ids: List of employee IDs

        Returns:
            List of employee dicts
        """
        if not employee_ids:
            return []

        # Build placeholders for IN clause
        placeholders = ','.join('?' * len(employee_ids))

        query = f"""
            SELECT 
                e.EmployeeId,
                e.FullName,
                e.Email,
                e.Designation,
                e.Location,
                e.YearsOfExperience as TotalExperience,
                e.AvailabilityStatus,
                e.PhoneNumber,
                t.TeamName,
                t.Department
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.TeamId
            WHERE e.EmployeeId IN ({placeholders})
        """

        return self.execute_query(query, tuple(employee_ids))

    def get_skills_batch(self, employee_ids):
        """
        Get skills for multiple employees in one query (EFFICIENT!)

        Args:
            employee_ids: List of employee IDs

        Returns:
            Dict mapping employee_id -> list of skills
        """
        if not employee_ids:
            return {}

        placeholders = ','.join('?' * len(employee_ids))

        query = f"""
            SELECT 
                es.EmployeeId,
                s.SkillName,
                s.Category,
                es.YearsOfExperience,
                es.ProficiencyLevel,
                es.LastUsedDate
            FROM EmployeeSkills es
            INNER JOIN Skills s ON es.SkillId = s.SkillId
            WHERE es.EmployeeId IN ({placeholders})
            ORDER BY es.EmployeeId, es.YearsOfExperience DESC
        """

        results = self.execute_query(query, tuple(employee_ids))

        # Group by employee_id
        skills_by_employee = {}
        for row in results:
            emp_id = row['EmployeeId']
            if emp_id not in skills_by_employee:
                skills_by_employee[emp_id] = []

            skills_by_employee[emp_id].append({
                'skill_name': row['SkillName'],
                'category': row['Category'],
                'years_of_experience': row['YearsOfExperience'],
                'proficiency_level': row['ProficiencyLevel'],
                'last_used_date': row['LastUsedDate']
            })

        return skills_by_employee

    def get_domains_batch(self, employee_ids):
        """
        Get domains for multiple employees in one query

        Args:
            employee_ids: List of employee IDs

        Returns:
            Dict mapping employee_id -> list of domains
        """
        if not employee_ids:
            return {}

        placeholders = ','.join('?' * len(employee_ids))

        query = f"""
            SELECT 
                ed.EmployeeId,
                d.DomainName,
                d.Category,
                ed.YearsOfExperience,
                ed.ProficiencyLevel
            FROM EmployeeDomains ed
            INNER JOIN Domains d ON ed.DomainId = d.DomainId
            WHERE ed.EmployeeId IN ({placeholders})
        """

        results = self.execute_query(query, tuple(employee_ids))

        # Group by employee_id
        domains_by_employee = {}
        for row in results:
            emp_id = row['EmployeeId']
            if emp_id not in domains_by_employee:
                domains_by_employee[emp_id] = []

            domains_by_employee[emp_id].append({
                'domain_name': row['DomainName'],
                'category': row['Category'],
                'years_of_experience': row['YearsOfExperience'],
                'proficiency_level': row['ProficiencyLevel']
            })

        return domains_by_employee

    def search_employees_sql(self, query_requirements):
        """
        Advanced SQL search with experience filtering
        This can be used as an alternative or complement to vector search

        Args:
            query_requirements: Parsed query with skills, experience, location, etc.

        Returns:
            List of matching employee IDs
        """
        conditions = []
        params = []

        # Base query
        query = """
            SELECT DISTINCT e.EmployeeId
            FROM Employees e
        """

        joins = []

        # Skill filtering
        required_skills = query_requirements.get('skills', [])
        if required_skills:
            joins.append("""
                INNER JOIN EmployeeSkills es ON e.EmployeeId = es.EmployeeId
                INNER JOIN Skills s ON es.SkillId = s.SkillId
            """)

            skill_conditions = []
            for skill in required_skills:
                skill_conditions.append("s.SkillName = ?")
                params.append(skill)

            conditions.append(f"({' OR '.join(skill_conditions)})")

        # Experience filtering
        experience_req = query_requirements.get('min_years_experience')
        experience_context = query_requirements.get('experience_context', {})

        if experience_req:
            operator_map = {
                'gt': '>',
                'gte': '>=',
                'lt': '<',
                'lte': '<=',
                'eq': '='
            }

            operator = query_requirements.get('experience_operator', 'gte')
            sql_operator = operator_map.get(operator, '>=')

            if experience_context.get('type') == 'skill_specific':
                # Skill-specific experience
                target_skill = experience_context.get('skill')
                if target_skill:
                    if not joins:  # Add join if not already added
                        joins.append("""
                            INNER JOIN EmployeeSkills es ON e.EmployeeId = es.EmployeeId
                            INNER JOIN Skills s ON es.SkillId = s.SkillId
                        """)

                    conditions.append(f"es.YearsOfExperience {sql_operator} ?")
                    params.append(experience_req)

                    conditions.append("s.SkillName = ?")
                    params.append(target_skill)

            else:
                # Total experience
                conditions.append(f"e.YearsOfExperience {sql_operator} ?")
                params.append(experience_req)

        # Location filtering
        location = query_requirements.get('location')
        if location:
            conditions.append("e.Location = ?")
            params.append(location)

        # Availability filtering
        availability = query_requirements.get('availability_status')
        if availability:
            conditions.append("e.AvailabilityStatus = ?")
            params.append(availability)

        # Build final query
        if joins:
            query += ' '.join(joins)

        if conditions:
            query += " WHERE " + ' AND '.join(conditions)

        # Execute
        results = self.execute_query(query, tuple(params) if params else None)

        return [row['EmployeeId'] for row in results]

    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.connection = None