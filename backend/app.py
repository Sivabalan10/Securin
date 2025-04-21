import ijson
import sqlalchemy
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import desc, or_
from sqlalchemy.schema import UniqueConstraint
import json
import math
import re
import ijson
from flask_cors import CORS
import ijson
from dotenv import load_dotenv
import os
from parse_data import is_nan, clean_nutrients
from flasgger import Swagger
import redis

app = Flask(__name__)
CORS(app) # to enable cross origin resource sharing for frontend access

swagger = Swagger(app)

load_dotenv()

try:
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    r.set("test_key", "Hello Redis!")
    print("Redis is working...", r.get("test_key").decode())
except redis.ConnectionError as e:
    print("Redis connection failed :", e)


# DATABASE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') # to get url from environment for safety purpose
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # to improve performance
db = SQLAlchemy(app)

# to create a databbas
class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    cuisine = db.Column(db.String(100))
    title = db.Column(db.String(255))
    rating = db.Column(db.Float)
    prep_time = db.Column(db.Integer)
    cook_time = db.Column(db.Integer)
    total_time = db.Column(db.Integer)
    description = db.Column(db.Text)
    nutrients = db.Column(JSONB)
    serves = db.Column(db.String(100))

    __table_args__ = (UniqueConstraint('title', 'cuisine', name='unique_title_cuisine'),) # to ensure the unique records


def load_recipes_from_json_in_chunks(json_file_path, chunk_size=1000):
    seen_recipes = set()  # To avoid duplicates within a single batch
    batch = []

    with open(json_file_path, 'r') as f:
        for key, item in ijson.kvitems(f, ''):
            title = item.get("title")
            cuisine = item.get("cuisine")
            unique_key = (title, cuisine)

            # Skip if already seen in current batch
            if unique_key in seen_recipes:
                continue

            # Skip if already in database
            if db.session.query(Recipe.id).filter_by(title=title, cuisine=cuisine).first():
                continue

            seen_recipes.add(unique_key)

            try:
                nutrients = item.get("nutrients", {})
                clean_nutrient_data = clean_nutrients(nutrients)
            except Exception as e:
                clean_nutrient_data = {}

            recipe = Recipe(
                cuisine=cuisine,
                title=title,
                rating=item.get("rating") if not is_nan(item.get("rating")) else None,
                prep_time=item.get("prep_time") if not is_nan(item.get("prep_time")) else None,
                cook_time=item.get("cook_time") if not is_nan(item.get("cook_time")) else None,
                total_time=item.get("total_time") if not is_nan(item.get("total_time")) else None,
                description=item.get("description"),
                nutrients=clean_nutrient_data,
                serves=item.get("serves")
            )

            batch.append(recipe)

            # Insert in chunks
            if len(batch) >= chunk_size:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
                seen_recipes.clear()

    # Final commit
    if batch:
        db.session.bulk_save_objects(batch)
        db.session.commit()

def apply_filter(query, field, condition):
    match = re.match(r'(<=|>=|<|>|=)(\d+)', condition)
    if match:
        op, value = match.groups()
        value = float(value)
        if op == '>':
            return query.filter(field > value)
        elif op == '<':
            return query.filter(field < value)
        elif op == '>=':
            return query.filter(field >= value)
        elif op == '<=':
            return query.filter(field <= value)
        elif op == '=':
            return query.filter(field == value)
    return query

def serialize_recipe(recipe):
    return {
        "id": recipe.id,
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "rating": recipe.rating,
        "prep_time": recipe.prep_time,
        "cook_time": recipe.cook_time,
        "total_time": recipe.total_time,
        "description": recipe.description[:80] + '...' if recipe.description else '',
        "nutrients": recipe.nutrients,
        "serves": recipe.serves
    }


@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """
    Get Paginated Recipes
    ---
    summary: Get paginated list of recipes
    description: Returns a paginated list of recipes ordered by rating in descending order.
    parameters:
      - in: query
        name: page
        schema:
          type: integer
          default: 1
        description: Page number
      - in: query
        name: limit
        schema:
          type: integer
          default: 10
        description: Number of recipes per page
    responses:
      200:
        description: A paginated list of recipes
        content:
          application/json:
            schema:
              type: object
              properties:
                page:
                  type: integer
                limit:
                  type: integer
                total:
                  type: integer
                data:
                  type: array
                  items:
                    type: object
                    properties:
                    id:
                        type: integer
                    title:
                        type: string
                    cuisine:
                        type: string
                    rating:
                        type: number
                    prep_time:
                        type: integer
                    cook_time:
                        type: integer
                    total_time:
                        type: integer
                    description:
                        type: string
                    nutrients:
                        type: object
                    serves:
                        type: string
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
    except Exception as e:
        return jsonify({'error': 'Invalid query parameters'}), 400
    
    total = Recipe.query.count()

     # input validation
    isvalid_params = True
    total_pages = math.ceil(total / limit)
    # limit
    if limit == 10 or limit == 50 or limit == 100:
        print("Query parameter limit is valid")
    else:
        isvalid_params = False
    # page
    if page > 0 and page <= total_pages:
        print("Query parameter page is valid")
    else:
        isvalid_params = False

    if isvalid_params:
        cache_key = f"data:{limit}:{page}"

        try:
            cached_data = r.get(cache_key)
        except redis.ConnectionError as e:
            print("Redis connection failed :", e)
            cached_data = None
        
        if cached_data:
            print("Data served from Redis cache")
            return jsonify(json.loads(cached_data))  # Deserialize JSON
    
        recipes = Recipe.query.order_by(desc(Recipe.rating)).offset(offset).limit(limit).all()

        data = [serialize_recipe(r) for r in recipes]
        response = {"page": page, "limit": limit, "total": total, "data": data}

        # Store the response in Redis cache
        try:
            r.setex(cache_key, 600, json.dumps(response)) # Cache for 10 minutes
            print("Data cached in Redis")
        except redis.ConnectionError as e:
            print("Redis connection failed :", e)

        return jsonify(response)
    else:
        return jsonify({'error': 'Invalid query parameters'}), 400

@app.route('/api/recipes/search', methods=['GET'])
def search_recipes():
    """
    Search Recipes
    ---
    summary: Search recipes with filters
    description: Search for recipes using optional filters like title, cuisine, rating, total_time, and calories.
    parameters:
      - in: query
        name: title
        schema:
          type: string
        description: Filter recipes by title (partial match)
      - in: query
        name: cuisine
        schema:
          type: string
        description: Filter recipes by cuisine (partial match)
      - in: query
        name: rating
        schema:
          type: string
        description: Filter by rating (supports >, <, >=, <=, =)
      - in: query
        name: total_time
        schema:
          type: string
        description: Filter by total time (supports >, <, >=, <=, =)
      - in: query
        name: calories
        schema:
          type: string
        description: Filter by calories (supports >, <, >=, <=, =)
      - in: query
        name: limit
        schema:
          type: integer
          default: 10
        description: Number of results per page
      - in: query
        name: page
        schema:
          type: integer
          default: 1
        description: Page number
    responses:
      200:
        description: Filtered list of recipes
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: array
                  items:
                    type: object
                    properties:
                    id:
                        type: integer
                    title:
                        type: string
                    cuisine:
                        type: string
                    rating:
                        type: number
                    prep_time:
                        type: integer
                    cook_time:
                        type: integer
                    total_time:
                        type: integer
                    description:
                        type: string
                    nutrients:
                        type: object
                    serves:
                        type: string
                total:
                  type: integer
    """

    query = Recipe.query
    try:
        title = request.args.get('title')
        cuisine = request.args.get('cuisine')
        rating = request.args.get('rating')
        total_time = request.args.get('total_time')
        calories = request.args.get('calories')
        per_page = int(request.args.get('limit', 10))
        page = int(request.args.get('page', 1))

        # input validation
        isvalid_params = True
        # limit
        if per_page == 10 or per_page == 50 or per_page == 100:
            print("Query parameter limit is valid")
        else:
            isvalid_params = False


        if isvalid_params:
            if title:
                query = query.filter(Recipe.title.ilike(f"%{title}%"))

            if cuisine:
                query = query.filter(Recipe.cuisine.ilike(f"%{cuisine}%"))

            if rating:
                query = apply_filter(query, Recipe.rating, rating)

            if total_time:
                query = apply_filter(query, Recipe.total_time, total_time)

            if calories:
                cal_value = int(re.sub(r'[^0-9]', '', calories))
                operator = re.findall(r'(<=|>=|<|>|=)', calories)
                if operator:
                    op = operator[0]
                    if op == '>':
                        query = query.filter(Recipe.nutrients['calories'].astext.op('~')(f'\\d+') & (Recipe.nutrients['calories'].astext.cast(db.Integer) > cal_value))
                    elif op == '<':
                        query = query.filter(Recipe.nutrients['calories'].astext.cast(db.Integer) < cal_value)
                    elif op == '>=':
                        query = query.filter(Recipe.nutrients['calories'].astext.cast(db.Integer) >= cal_value)
                    elif op == '<=':
                        query = query.filter(Recipe.nutrients['calories'].astext.cast(db.Integer) <= cal_value)
                    elif op == '=':
                        query = query.filter(Recipe.nutrients['calories'].astext.cast(db.Integer) == cal_value)

        else:
            return jsonify({'error': 'Invalid query parameters'}), 400

    except Exception as e:
        return jsonify({'error': 'Invalid query parameters'}), 400
    
    # redis implementation
    cache_key = f"data:{page}:{per_page}:{title}:{cuisine}:{rating}:{total_time}:{calories}"


    try:
        cached_data = r.get(cache_key)
    except redis.ConnectionError as e:
        print("Redis connection failed :", e)
        cached_data = None
    
    if cached_data:
        print("Data served from Redis cache")
        return jsonify(json.loads(cached_data))  # Deserialize JSON
    
    total = query.count()
    paginated = query.offset((page - 1) * per_page).limit(per_page).all()
    response = {
        "data": [serialize_recipe(r) for r in paginated],
        "total": total
    }

    # Store the response in Redis cache
    try:
        r.setex(cache_key, 600, json.dumps(response)) # Cache for 10 minutes
        print("Data cached in Redis")
    except redis.ConnectionError as e:
        print("Redis connection failed :", e)

    return jsonify(response)

@app.route('/load_data')
def load_data():
    with app.app_context():
        db.create_all()
        print("Tables created..")
        load_recipes_from_json_in_chunks('US_recipes_null.json', chunk_size=1000)
    return "Data Loaded Successfully"


if __name__ == "__main__":
    app.run(debug = True)


