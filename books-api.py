from flask import Flask, jsonify, request
from flask_mongoengine import MongoEngine
from mongoengine import connect, Document, StringField, FloatField, DoesNotExist, ValidationError
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
# from api_constants import mongdb_username, mongodb_pass, mongodb_hostname, mongdb_dbname, secret_key, UPLOAD_FOLDER, \
#     ALLOWED_EXTENSIONS


import urllib
import jwt
from datetime import datetime, timedelta
from functools import wraps
# from  flask_mysqldb import MySQL
import pymysql
from flask_cors import CORS
from werkzeug.utils import secure_filename
import _osx_support
import os
# import MySQLdb.cursors
# import re
# from datetime import timedelta


app = Flask(__name__)

DB_URI = "mongodb+srv://kishoreshankar:Kishore123@cluster0.ihqyusx.mongodb.net/?retryWrites=true&w=majority"
mongdb_username = "kishore"
mongdb_dbname = "API"
mongodb_pass = "123456"
secret_key = "mysecretkey"
UPLOAD_FOLDER = '/Users/naikajshiradkar'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
# .format(
#     urllib.parse.quote_plus(mongdb_username), urllib.parse.quote_plus(mongodb_pass), mongodb_hostname, mongdb_dbname,
# )

# Setting up the app config
app.config["MONGODB_HOST"] = DB_URI
app.config['JWT_SECRET_KEY'] = secret_key
app.config['JWT_EXPIRATION_DELTA'] = timedelta(minutes=15)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# db = MongoEngine()
# db.init_app(app)

# CORS(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

connect(host=app.config['MONGODB_HOST'])


@app.route("/")
def index():
    return "Hello, World!"


# setting up data models
class User(Document):
    username = StringField(required=True, max_length=100)
    password = StringField(required=True, max_length=100)


class Book(Document):
    title = StringField(required=True, max_length=100)
    author = StringField(required=True, max_length=100)
    price = StringField(required=True, max_value=120)


# public routes below. These endpoints are public and can be accessed without auth.
@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        raise BadRequest("Please provide username and password")

    try:
        user = User(username=username, password=password)
        user.save()
        return jsonify({'message': 'User created successfully'}), 201
    except (ValueError, KeyError):
        raise BadRequest("Invalid user data")


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        raise BadRequest("Please provide username and password")

    try:
        user = User.objects.get(username=username, password=password)
    except DoesNotExist:
        raise BadRequest("Invalid username or password")

    # generate JWT token
    payload = {
        'user_id': str(user.id),
        'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }
    token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token}), 200


def authenticate_user(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        return user
    except Exception:
        return None


# create route for CRUD operations
@app.route('/books', methods=['POST'])
def create_book():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise BadRequest("Please provide an authorization header")

    token = auth_header.split(" ")[1]
    user = authenticate_user(token)
    if not user:
        raise BadRequest("Invalid or expired token")

    try:
        
        book_data_list = request.json
        print(book_data_list)
        books = []
        
        
        book = Book(title=book_data_list['title'],author=book_data_list['author'],price=book_data_list['price'])
        book.save()
        books.append(book)

        return [book.to_json() for book in books], 201

    except (ValueError, KeyError):
        raise BadRequest("Invalid book data")


# It returns list of books and their ids only, which we have made public for the app.
@app.route('/books', methods=['GET'])
def get_all_books():
    books = Book.objects.only('title')
    # Construct a list of dictionaries containing only the title and ID fields
    book_list = [{'id': str(book.id), 'title': book.title} for book in books]
    return {'books': book_list}, 200


@app.route('/books/search', methods=['GET'])
def search_books():
    title = request.args.get('title')
    if not title:
        raise BadRequest("Please provide a book title to search for")

    # Perform a case-insensitive search for books with the given title
    books = Book.objects(title=title).only('title')

    # Construct a list of dictionaries containing only the title and ID fields
    book_list = [{'id': str(book.id), 'title': book.title} for book in books]

    return {'books': book_list}, 200


# private routes below
@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise BadRequest("Please provide an authorization header")

    token = auth_header.split(" ")[1]
    user = authenticate_user(token)
    if not user:
        raise BadRequest("Invalid or expired token")
    try:
        book = Book.objects.get(id=book_id)
        return book.to_json(), 200
    except DoesNotExist:
        raise NotFound("Book not found")
    except ValidationError:
        raise BadRequest("Invalid book ID")


@app.route('/books/<book_id>', methods=['PUT'])
def update_book(book_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise BadRequest("Please provide an authorization header")

    token = auth_header.split(" ")[1]
    user = authenticate_user(token)
    if not user:
        raise BadRequest("Invalid or expired token")

    try:
        book = Book.objects(id=book_id).first()
        if not book:
            raise NotFound("Book not found")
        book_data = request.json
        book.update(**book_data)
        return book.to_json(), 200
    except (ValueError, KeyError):
        raise BadRequest("Invalid book data")


@app.route('/books/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise BadRequest("Please provide an authorization header")

    token = auth_header.split(" ")[1]
    user = authenticate_user(token)
    if not user:
        raise BadRequest("Invalid or expired token")
    try:
        book = Book.objects.get(id=book_id)
        book.delete()
        return '', 204  # returning No Content after deletion
    except DoesNotExist:
        raise NotFound("Book not found")
    except ValidationError:
        raise BadRequest("Invalid book ID")


@app.route('/protected', methods=['GET'])
def protected():
    token_str = request.headers.get('Authorization')
    if not token_str:
        raise BadRequest("Token is missing")

    try:
        token = token_str.split()[1]
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        return jsonify({'message': 'Welcome, {}!'.format(user.username)}), 200
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.ExpiredSignatureError):
        raise BadRequest("Invalid token")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_size(filesize):
    max_size = 2 * 1024 * 1024  # 2 MB
    return int(filesize) <= max_size


@app.route('/upload-file', methods=['POST'])
def upload_file():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise BadRequest("Please provide an authorization header")

    token = auth_header.split(" ")[1]
    user = authenticate_user(token)
    if not user:
        raise BadRequest("Invalid or expired token")

    if not request.files.__len__():
        raise BadRequest('No file part')

    file = request.files.values().__next__()
    if file.filename == '':
        raise BadRequest('No selected file')

    if file and allowed_file(file.filename) and allowed_size(request.headers.get('Content-Length')):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'message': 'File uploaded successfully'}), 200
    else:
        raise BadRequest('Invalid file type')


@app.errorhandler(BadRequest)
@app.errorhandler(NotFound)
@app.errorhandler(InternalServerError)
def handle_errors(error):
    response = jsonify({'error': str(error)})
    response.status_code = error.code if hasattr(error, 'code') else 500
    return response


if __name__ == '__main__':
    app.run(debug=True)  
