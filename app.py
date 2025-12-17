# app.py
# Flask API for Natural Language Query Processing
# FIXED VERSION - No double wrapping in /parse endpoint

from flask import Flask, request, jsonify
from flask_cors import CORS
from services.query_parser import get_parser
from services.database import DatabaseService
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
parser = get_parser()
db_service = DatabaseService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Just check if parser is loaded (skip database check for now)
        parser_healthy = parser is not None and parser.nlp is not None
        
        return jsonify({
            'status': 'healthy' if parser_healthy else 'degraded',
            'model_loaded': parser_healthy,
            'service': 'AI Talent Search API',
            'entity_types': parser.get_entity_types() if parser_healthy else []
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/parse', methods=['POST'])
def parse_query_endpoint():
    """
    Parse natural language query and extract entities

    ✅ FIXED: Returns result directly without extra wrapping
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'error': 'Missing query parameter'
            }), 400

        query = data['query']

        logger.info(f"Parsing query: {query}")

        # Parse the query
        result = parser.parse_query(query)

        # ✅ Return result DIRECTLY - no extra wrapping!
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error parsing query: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'original_query': data.get('query', ''),
            'parsed': {
                'skills': [],
                'categories': [],
                'category_skills': [],
                'min_years_experience': None,
                'experience_operator': 'gte',
                'experience_context': None,
                'location': None,
                'availability_status': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            },
            'applied_filters': [],
            'skills_found': 0
        }), 500


@app.route('/chat', methods=['POST'])
def chat_search():
    """
    Full search endpoint - parse query and return matching employees
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'error': 'Missing query parameter'
            }), 400

        query = data['query']

        logger.info(f"Processing search query: {query}")

        # Step 1: Parse the query
        parse_result = parser.parse_query(query)

        if 'error' in parse_result:
            return jsonify({
                'error': parse_result['error'],
                'original_query': query
            }), 500

        # Step 2: Extract search criteria
        parsed_data = parse_result['parsed']
        skills = parsed_data.get('skills', [])
        category_skills = parsed_data.get('category_skills', [])
        all_skills = list(set(skills + category_skills))

        min_years = parsed_data.get('min_years_experience')
        exp_operator = parsed_data.get('experience_operator', 'gte')
        exp_context = parsed_data.get('experience_context')
        location = parsed_data.get('location')
        availability = parsed_data.get('availability_status')

        logger.info(f"Search criteria - Skills: {all_skills}, Years: {min_years}, Location: {location}")

        # Step 3: Search database
        if not all_skills:
            logger.warning("No skills found in query")
            return jsonify({
                'original_query': query,
                'parsed': parsed_data,
                'results': [],
                'total_results': 0,
                'search_method': 'sql',
                'message': 'No skills detected in query'
            }), 200

        # Get matching employees
        employees = db_service.search_employees(
            skills=all_skills,
            min_years=min_years,
            operator=exp_operator,
            experience_context=exp_context,
            location=location,
            availability=availability
        )

        logger.info(f"Found {len(employees)} matching employees")

        # Step 4: Return results
        return jsonify({
            'original_query': query,
            'parsed': parsed_data,
            'results': employees,
            'total_results': len(employees),
            'search_method': 'sql'
        }), 200

    except Exception as e:
        logger.error(f"Error in chat search: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'original_query': data.get('query', ''),
            'results': [],
            'total_results': 0
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get API statistics"""
    try:
        parser_stats = parser.get_stats()
        db_stats = db_service.get_stats()

        return jsonify({
            'parser': parser_stats,
            'database': db_stats
        }), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask API...")
    logger.info(f"Parser loaded: {parser.nlp is not None}")
    logger.info(f"Entity types: {parser.get_entity_types()}")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

