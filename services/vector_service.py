import chromadb
from chromadb.config import Settings
from pathlib import Path


class VectorService:
    def __init__(self, persist_dir="./chroma_db", collection_name="employee_skills"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        # Initialize ChromaDB with default embeddings
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False
        ))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def create_employee_document(self, employee_data):
        """Create searchable document from employee data"""
        parts = []

        # Basic info
        parts.append(f"{employee_data.get('full_name', '')}")
        parts.append(f"{employee_data.get('designation', '')} developer")
        parts.append(f"located in {employee_data.get('location', '')}")
        parts.append(f"{employee_data.get('availability', '')} availability")

        # Skills with context
        skills = employee_data.get('skills', [])
        for skill in skills:
            skill_text = f"{skill['name']} {skill.get('years', 0)} years experience {skill.get('level', '')}"
            parts.append(skill_text)

        # Projects
        projects = employee_data.get('projects', [])
        for project in projects:
            parts.append(f"worked on {project.get('name', '')}")

        return " | ".join(parts)

    def index_employee(self, employee_id, employee_data):
        """Index an employee for semantic search"""
        document = self.create_employee_document(employee_data)

        # Build skills with years for metadata
        skills_list = employee_data.get('skills', [])
        skills_str = ','.join([s['name'] for s in skills_list])

        # Store skill details in metadata (NEW - for match calculation)
        skill_years = {}
        for skill in skills_list:
            skill_years[skill['name'].lower()] = skill.get('years', 0)

        metadata = {
            'employee_id': employee_id,
            'full_name': employee_data.get('full_name', ''),
            'location': employee_data.get('location', ''),
            'designation': employee_data.get('designation', ''),
            'availability': employee_data.get('availability', ''),
            'skills': skills_str,
            'total_experience': employee_data.get('total_experience', 0),  # NEW
            # Store as JSON string for skill years
            'skill_years': str(skill_years)  # NEW - stringified dict
        }

        self.collection.upsert(
            ids=[str(employee_id)],
            documents=[document],
            metadatas=[metadata]
        )

        return {
            'employee_id': employee_id,
            'indexed': True,
            'document_length': len(document)
        }

    def search(self, query_text, n_results=20, filters=None):
        """Semantic search for employees"""
        where_clause = None

        if filters:
            conditions = []
            if filters.get('location'):
                conditions.append({"location": {"$eq": filters['location']}})
            if filters.get('availability'):
                conditions.append({"availability": {"$eq": filters['availability']}})

            if len(conditions) == 1:
                where_clause = conditions[0]
            elif len(conditions) > 1:
                where_clause = {"$and": conditions}

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_clause,
            include=["metadatas", "distances", "documents"]
        )

        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, emp_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0
                similarity = max(0, 1 - distance)  # Convert distance to similarity

                formatted_results.append({
                    'employee_id': int(emp_id),
                    'similarity_score': round(similarity * 100, 1),
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'document': results['documents'][0][i] if results['documents'] else ''
                })

        # Sort by similarity score
        formatted_results.sort(key=lambda x: x['similarity_score'], reverse=True)

        return formatted_results

    def delete_employee(self, employee_id):
        """Remove employee from index"""
        self.collection.delete(ids=[str(employee_id)])
        return {'employee_id': employee_id, 'deleted': True}

    def get_stats(self):
        """Get collection statistics"""
        return {
            'collection_name': self.collection_name,
            'count': self.collection.count()
        }

    def clear_all(self):
        """Clear all data from collection"""
        # Delete and recreate collection
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        return {'cleared': True}
