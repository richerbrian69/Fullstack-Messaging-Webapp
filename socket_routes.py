'''
socket_routes
file containing all the routes related to socket.io
'''

from flask_socketio import join_room, emit, leave_room
from flask import request

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room
from app import extract_session_data

import db

room = Room()

# session id dictionary to submit socket events for management of friends list
online_users_and_sid = {}
# cookies dictionary storing authentication token
online_user_cookies = {}

def emit_to_friends(event, data):
    """
    Emit a socket event to all friends of the user in the specified room.
    """
    # Retrieve friends of the user from your data store
    friends = db.get_friends(data[0])  # Implement this function to get friends of the user
    # Emit event to each friend
    for friend in friends:
        if friend in online_users_and_sid:
            emit(event, data, room=online_users_and_sid[friend])


@socketio.on('login')
def get_statuses(username):
    friend_statuses = []
    friends = db.get_friends(username)
    for friend in friends:
        if friend in online_users_and_sid:
            is_online = True
        else:
            is_online = False
        friend_statuses.append({'username': friend, 'is_online': is_online})
    return friend_statuses
    
# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    session_id = request.sid
    online_users_and_sid[username] = session_id
    emit_to_friends("friend_status_update", (username, True))
    if room_id is None or username is None:
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
    join_room(int(room_id))
    emit("incoming", (f"{username} has connected", "green"), to=int(room_id))

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    leave_room(room_id)
    emit_to_friends("friend_status_update", (username, False))
    try:
        del online_users_and_sid[username]
    except KeyError:
        pass
    if room_id is None or username is None:
        return
    emit("incoming", (f"{username} has disconnected", "red"), to=int(room_id))

# acknowledge message received
@socketio.on('received')
def received(room_id):
    emit("received", to=int(room_id), include_self=False)
    
# send message event handler
@socketio.on("send")
def send(username, message, room_id):
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return
    db.store_message(username, message, room_id)
    emit("receive", (username, f"{message}"), to=int(room_id), include_self=False)
    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return    
    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"
    room_id = room.get_room_id(sender_name, receiver_name)
    # if the both users are already inside of a room 
    if room_id is not None:
        # THEY ARE IN ROOM TOGETHER ALREADY
        join_room(room_id)
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.", "green"), to=room_id, include_self=False)
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"))
        return room_id

    # no room for the pair
    room_id = room.create_room(sender_name, receiver_name)
    members = [sender_name, receiver_name]
    try:
        db.create_room(room_id, members)
    except:
        pass
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"), to=room_id)
    return room_id

@socketio.on("join_room")
def join_chatroom(sender_name, id):
    join_room(id)
    emit("incoming", (f"{sender_name} has joined the room.", "green"), to=id, include_self=False)
    # emit only to the sender
    emit("incoming", (f"You have joined the room.", "green"))
    return int(id)

# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != online_user_cookies[username]:
            emit("incoming", "You are not authenticated")
            return
    except KeyError:
        emit("incoming", "You are not authenticated")
        return
    emit("incoming", (f"{username} has left the room.", "red"), to=int(room_id), include_self=False)
    emit("incoming", ("You have left the previous room", "red"));
    leave_room(int(room_id))

# emit signal to user that they have a new friend request
@socketio.on("add_friend")
def add_friend(username, friend_username):
    session_cookie = request.cookies.get("session_id")
    if not session_cookie:
        return
    try:
        session_data = extract_session_data(session_cookie)
        if session_data != online_user_cookies[username]:
            emit("incoming", "You are not authenticated")
            return
    except KeyError:
        emit("incoming", "You are not authenticated")
        return
    try:
        friend_socket_id = online_users_and_sid[friend_username]
    except KeyError:
        return
    
    if friend_socket_id:
        emit("incoming_friend_request", username, to=friend_socket_id)
    else:
        return
    
# emit signal to user that they have been removed as a friend
@socketio.on("removed_friend")
def removed_friend(username, friend_username):
    try:
        friend_socket_id = online_users_and_sid[friend_username]
    except KeyError:
        return
    
    if friend_socket_id:
        emit("update_outgoing", username, to=friend_socket_id)
    else:
        return

# emit signal to acknowledge friend request is handled
@socketio.on("handled_request")
def handled_request(username, friend_username):
    try:
        friend_socket_id = online_users_and_sid[friend_username]
    except KeyError:
        return
    
    if friend_socket_id:
        emit("update_outgoing", username, to=friend_socket_id)
    else:
        return
    