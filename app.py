from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
from pathlib import Path

from config import Config
from services.resume_parser import ResumeParser
from services.query_parser import QueryParser
from services.vector_service import VectorService
from services.validator import ApplicationValidator

# -------------------------------------------------
# Flask App Setup
# -------------------------------------------------
app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# -------------------------------------------------
# Service instances (lazy initialized)
# -------------------------------------------------
resume_parser = None
query_parser = None
vector_service = None
validator = None


def init_services():
    """Initialize all heavy services safely (Gunicorn compatible)"""
    global resume_parser, query_parser, vector_service, validator

    if resume_parser is None:
        print("Initializing services...")
        resume_parser = ResumeParser()
        query_parser = QueryParser()
        vector_service = VectorService()
        validator = ApplicationValidator()
        print("Services initialized successfully!")


# -------------------------------------------------
# Ensure services initialize once (Gunicorn-safe)
# -------------------------------------------------
@app.before_first_request
def startup():
    init_services()


# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'services': {
            'resume_parser': resume_parser is not None,
            'query_parser': query_parser is not None,
            'vector_service': vector_service is not None,
            'validator': validator is not None
        },
        'vector_db_count': vector_service.get_stats()['count'] if vector_service else 0
    })


# -------------------------------------------------
# Resume Parsing
# -------------------------------------------------
@app.route('/parse', methods=['POST'])
def parse_resume():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            result = resume_parser.parse_resume(tmp_path)
            return jsonify(result)
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------
# Chat / Query Parsing + Vector Search
# -------------------------------------------------
@app.route('/chat', methods=['POST'])
def parse_and_search():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400

        query = data['query']

        parsed = query_parser.parse_query(query)

        search_parts = []
        if parsed['parsed']['skills']:
            search_parts.append(' '.join(parsed['parsed']['skills']))
        if parsed['parsed']['location']:
            search_parts.append(parsed['parsed']['location'])
        if parsed['parsed']['availability_status']:
            search_parts.append(parsed['parsed']['availability_status'])

        search_text = query if not search_parts else ' '.join(search_parts)

        filters = {}
        if parsed['parsed']['location']:
            filters['location'] = parsed['parsed']['location']
        if parsed['parsed']['availability_status']:
            filters['availability'] = parsed['parsed']['availability_status']

        vector_results = vector_service.search(
            search_text,
            n_results=20,
            filters=filters if filters else None
        )

        enriched_results = []
        for result in vector_results:
            match_info = validator.calculate_query_match(
                employee_data=result,
                query_requirements=parsed['parsed']
            )
            enriched_results.append({
                **result,
                'detailed_match': match_info
            })

        enriched_results.sort(
            key=lambda x: x['detailed_match']['overall_match_percentage'],
            reverse=True
        )

        return jsonify({
            **parsed,
            'vector_results': enriched_results,
            'search_text_used': search_text,
            'total_results': len(enriched_results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------
# Vector Index APIs
# -------------------------------------------------
@app.route('/vector/index', methods=['POST'])
def index_employee():
    data = request.get_json()
    if not data or 'employee_id' not in data:
        return jsonify({'error': 'No employee data provided'}), 400

    return jsonify(
        vector_service.index_employee(
            data['employee_id'],
            data.get('employee_data', {})
        )
    )


@app.route('/vector/index-batch', methods=['POST'])
def index_batch():
    data = request.get_json()
    employees = data.get('employees', [])

    results = [
        vector_service.index_employee(emp['employee_id'], emp)
        for emp in employees
    ]

    return jsonify({'indexed': len(results), 'results': results})


@app.route('/vector/search', methods=['POST'])
def search_employees():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400

    results = vector_service.search(
        data['query'],
        data.get('n_results', 20),
        data.get('filters')
    )

    return jsonify({'results': results, 'count': len(results)})


@app.route('/vector/stats', methods=['GET'])
def vector_stats():
    return jsonify(vector_service.get_stats())


@app.route('/vector/clear', methods=['POST'])
def clear_vector_db():
    return jsonify(vector_service.clear_all())


# -------------------------------------------------
# Local Run (NOT used by Gunicorn)
# -------------------------------------------------
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=10000,
        debug=False
    )
