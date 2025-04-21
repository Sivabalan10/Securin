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

def load_json_to_db(file_path, chunk):
    with open('US_recipes_null.json','r') as f:
        for key, value in ijson.kvitems(f,''):
            title = value.get("title")
            cuisine = value.get("cuisine")



def is_nan(val): # to verify it is null value or not
    try:
        return math.isnan(float(val))
    except:
        return False
    
def extract_numeric(val): # convert anydatatype to integer
    if isinstance(val, str):
        match = re.search(r'\d+', val)
        return int(match.group()) if match else None
    elif isinstance(val, (int, float)):
        return int(val)
    return None

def clean_nutrients(nutrients): # In nutrients, the values are in string format (233g). This function extracts 233 integer.
    numeric_nutrients = {}
    for key, val in nutrients.items():
        numeric_nutrients[key] = extract_numeric(val)
    return numeric_nutrients


