'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, render_template, request, abort, url_for, make_response, flash, redirect, jsonify
from flask_socketio import SocketIO
from itsdangerous import URLSafeSerializer, BadSignature
from time import sleep
import db
import secrets
import html
import uuid
import hashlib

# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

# don't remove this!!
import socket_routes

# function to convert password into hash
def hash_password(password):
    password_bytes = password.encode('utf-8')
    sha256_hash = hashlib.sha256()
    sha256_hash.update(password_bytes)
    hashed_password = sha256_hash.hexdigest()
    return hashed_password

# important 'itsdangerous' declarations
secret_key = "example secret key. Real key can be anything more complex"
serializer = URLSafeSerializer(secret_key)

# Function to verify and extract session data from the cookie
def extract_session_data(cookie_value):
    try:
        # Deserialize and verify the cookie value
        session_data = serializer.loads(cookie_value)
        return session_data
    except BadSignature:
        # The cookie value has been tampered with or is invalid
        return None

# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)
    username = request.json.get("username")
    username = html.escape(username)
    hashed_password = request.json.get("password")
    hashed_twice_password = hash_password(hashed_password)
    user =  db.get_user(username)
    if user is None:
        return "Error: User does not exist!"
    if hashed_twice_password != user.password:
        return "Error: Password does not match!"
    session_id = str(uuid.uuid4())
    serialized_session_id = serializer.dumps(session_id)
    socket_routes.online_user_cookies[username] = session_id
    response = make_response(url_for('home', username=username))
    response.set_cookie('session_id', serialized_session_id)
    return response

# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")

# handles a post request when the user clicks the signup button
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)
    username = request.json.get("username")
    if not (3 <= len(username) <= 20):
        return "Error: Username must be between 3 and 20 characters long."
    username = html.escape(username)
    hashed_password = request.json.get("password")
    salt = request.json.get("salt")
    user_type = request.json.get("userType")
    hashed_twice_password = hash_password(hashed_password)
    if db.get_user(username) is None:
        db.insert_user(username, hashed_twice_password, salt, user_type)
        session_id = str(uuid.uuid4())
        serialized_session_id = serializer.dumps(session_id)
        socket_routes.online_user_cookies[username] = session_id
        response = make_response(url_for('home', username=username))
        response.set_cookie('session_id', serialized_session_id)
        return response
    return "Error: User already exists!"

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

# home page, where the messaging app is
@app.route("/home")
def home():
    if request.args.get("username") is None:
        abort(404)
    username=request.args.get("username")
    username=html.escape(username)
    user = db.get_user(username)
    if user is None:
        abort(404)
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return redirect(url_for('index'))
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return redirect(url_for('index'))
    except KeyError:
        return redirect(url_for('index'))
    friends=db.get_friends_list(username)
    friend_requests=db.get_friend_requests(username)
    outgoing_friend_requests=db.get_outgoing_friend_requests(username)
    chatrooms=db.get_chatrooms(username)
    return render_template("home.jinja", 
                           user=user,
                           friends=friends,
                           friend_requests=friend_requests,
                           outgoing_friend_requests=outgoing_friend_requests,
                           group_chats=chatrooms
                           )

@app.route('/mute_user', methods=['POST'])
def mute_user():
    user_to_mute = request.json.get("user_to_mute")
    username = request.json.get("current_user")
    db.mute_user(user_to_mute)
    user = db.get_user(username)
    show_user = db.get_user(user_to_mute)
    return render_template('user_page.jinja', user=user, show_user=show_user)

@app.route('/unmute_user', methods=['POST'])
def unmute_user():
    user_to_mute = request.json.get("user_to_mute")
    username = request.json.get("current_user")
    db.unmute_user(user_to_mute)
    user = db.get_user(username)
    show_user = db.get_user(user_to_mute)
    return render_template('user_page.jinja', user=user, show_user=show_user)

@app.route('/user/<username>')
def user_page(username):
    show_user = db.get_user(username)
    current_username=request.cookies.get("username")
    current_user = db.get_user(current_username)
    if show_user is None:
        return jsonify({"error": "User does not exist!"}), 404
    return render_template('user_page.jinja', user=current_user, show_user=show_user)

@app.route('/update_bio', methods=['POST'])
def update_bio():
    current_username=request.cookies.get("username")
    current_user = db.get_user(current_username)
    content = request.form['bio']
    db.update_bio(current_username, content)
    return render_template('user_page.jinja', user=current_user, show_user=current_user)

@app.route('/forum')
def forum():
    session_cookie = request.cookies.get("session_id")
    username=request.cookies.get("username")
    user = db.get_user(username)
    if not session_cookie:
        return redirect(url_for('index'))
    articles = db.get_articles()
    return render_template("forum.jinja", user=user, articles=articles)

@app.route('/create_article', methods=['POST'])
def create_article():
    title = request.form['title']
    author = request.form['author']
    content = request.form['content']
    article = db.create_article(title=title, author=author, content=content)
    return redirect(url_for('forum'))

@app.route('/article/<string:title>')
def article_page(title):
    article = db.get_article_by_title(title)
    username=request.cookies.get("username")
    user = db.get_user(username)
    if article:
        return render_template("article_page.jinja", article=article, user=user)
    else:
        # Handle case where article with specified title is not found
        return "Article not found", 404
    
@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    # Retrieve the article from the database
    article = db.get_article_by_id(article_id)
    username = request.cookies.get("username")
    user = db.get_user(username)


    if request.method == 'POST':
        # Get the updated article data from the form
        updated_title = request.form['title']
        updated_content = request.form['content']

        # Update the article in the database
        db.update_article(article_id, updated_title, updated_content)
        article = db.get_article_by_title(updated_title)
        # Redirect to the article page after editing
        return render_template("article_page.jinja", article=article, user=user)
    else:
        # Render the edit article form with the current article data
        return render_template("edit_article.jinja", article=article, user=user)

@app.route('/delete_article/<int:article_id>', methods=['GET', 'POST'])
def delete_article(article_id):
    db.delete_article(article_id)
    return redirect(url_for('forum'))

@app.route('/delete_comment/<int:article_id>/<int:comment_id>', methods=['DELETE'])
def delete_comment(article_id, comment_id):
    article = db.get_article_by_id(article_id)
    db.remove_comment(article_id, comment_id)
    username=request.cookies.get("username")
    user = db.get_user(username)
    return render_template("article_page.jinja", article=article, user=user)

@app.route('/add_comment/<string:article_title>', methods=['POST'])
def add_comment(article_title):
    if request.method == 'POST':
        # Get the comment content from the form
        comment_content = request.form['comment']
        author = request.cookies.get("username")
        user = db.get_user(author)
        if user.is_muted:
            return "You do not have permission to post"
        # Add the comment to the article in the database
        db.add_comment_to_article_by_title(article_title, comment_content, author)
        
        # Redirect back to the article page
        return redirect(url_for('article_page', title=article_title))
    else:
        # Handle other HTTP methods if necessary
        return "Method Not Allowed", 405

# post request to add friend
@app.route('/add_friend', methods=['POST'])
def add_friend():
    friend_username = request.json.get('friendName')
    username=request.json.get("username")
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return "Not authenticated!"
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return "Not authenticated!"
    except KeyError:
        return "Not authenticated!"
    success = db.send_friend_request(username, friend_username)
    if success==1:
        return "Friend request sent"
    elif success==2:
        return "Friend request already pending"
    elif success==3:
        return "Error adding friend"
    elif success==4:
        return "Cant add yourself"
    return "Test"

# post request to remove friend
@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    friend_username = request.json.get('friendName')
    username=request.json.get("username")
    db.remove_friend(username, friend_username)
    return "Friend Removed"

# post request to get friend requests
@app.route('/get_friend_requests', methods=['POST'])
def get_friend_requests():
    username=request.json.get("username")
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return "Not authenticated!"
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return "Not authenticated!"
    except KeyError:
        return "Not authenticated!"
    req = db.get_friend_requests(username)
    return req

# post request to get outgoing friend requests
@app.route('/get_outgoing_friend_requests', methods=['POST'])
def get_outgoing_friend_requests():
    username=request.json.get("username")
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return "Not authenticated!"
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return "Not authenticated!"
    except KeyError:
        return "Not authenticated!"
    req = db.get_outgoing_friend_requests(username)
    return req

# post request to accept friend requests
@app.route('/accept_friend_requests', methods=['POST'])
def accept_friend_requests():
    username=request.json.get("username")
    friend_name=request.json.get("friendName")
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return "Not authenticated!"
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return "Not authenticated!"
    except KeyError:
        return "Not authenticated!"
    db.accept_friend_request(username, friend_name)
    return '1'

# post request to reject friend requests
@app.route('/reject_friend_requests', methods=['POST'])
def reject_friend_requests():
    username=request.json.get("username")
    friend_name=request.json.get("friendName")
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return "Not authenticated!"
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != socket_routes.online_user_cookies[username]:
            return "Not authenticated!"
    except KeyError:
        return "Not authenticated!"
    db.reject_friend_request(username, friend_name)
    return '1'

# post request to get friends list
@app.route('/get_friends', methods=['POST'])
def get_friends():
    username=request.json.get("username")
    f_list = db.get_friends_list(username)
    return f_list

# post request to get salt.
@app.route('/get_salt', methods=['POST'])
def get_salt():
    username=request.json.get("username")
    user = db.get_user(username)
    if user:
        return user.salt
    print("salt error")
    return "Salt error"

# post request to store message
# @app.route('/store_message', methods=['POST'])
# def store_message():
#     session_cookie = request.cookies.get("session_id")
#     username = request.json.get("username")
#     if not session_cookie:
#         return "Not authenticated!"
#     # try:
#     #     session_data = extract_session_data(session_cookie)
#     #     if session_data != socket_routes.online_user_cookies[username]:
#     #         return "Not authenticated!"
#     # except KeyError:
#     #     return "Not authenticated!"
#     friend = request.json.get("talking_to")
#     message = request.json.get("message_to_be_stored")
#     db.store_message(username, friend, message)
#     return 'Worked'

# post request to store public key
@app.route('/store_public_key', methods=['POST'])
def store_public_key():
    username = request.json.get('username')
    public_key = request.json.get('publicKey')
    db.store_key(username, public_key)
    return 'Done'

# get request to get public key of user
@app.route('/public_key/<username>', methods=['GET'])
def get_public_key_route(username):
    public_key = db.get_public_key(username)
    if public_key:
        return public_key['exportedPublicKey']
    else:
        return "Public Key not Found"
    
# get request to get public sig key of user
@app.route('/public_sig_key/<username>', methods=['GET'])
def get_public_sig_key_route(username):
    public_key = db.get_public_key(username)
    if public_key:
        return public_key['exportedPublicSigningKey']
    else:
        return "Public Key not Found"

# post request to get message history
@app.route('/get_message_history', methods=['POST'])
def get_message_history():
    session_cookie = request.cookies.get("session_id")
    room_id = request.cookies.get("room_id")
    if not session_cookie:
        return "Not authenticated!"
    # try:
    #     session_data = extract_session_data(session_cookie)
    #     if session_data != socket_routes.online_user_cookies[username]:
    #         return "Not authenticated!"
    # except KeyError:
    #     return "Not authenticated!"
    message_history = db.get_message_history(room_id)
    if message_history == 'Key Error!':
        return 'None'
    return message_history

@app.route('/create_chatroom', methods=['POST'])
def create_chatroom():
    members = request.json.get("highlightedNamesList")
    room_id = socket_routes.room.create_chatroom(members)
    db.create_chatroom(room_id, members)
    return str(room_id)

# RUN APP!
if __name__ == '__main__':
    socketio.run(app, debug=True, ssl_context=('./certs/localhost.crt', './certs/localhost.key'))
    # socketio.run(app)
