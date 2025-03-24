'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import *

from pathlib import Path

# creates the database directory
Path("database") \
    .mkdir(exist_ok=True)

# "database/main.db" specifies the database file
# change it if you wish
# turn echo = True to display the sql output
engine = create_engine("sqlite:///database/main.db", echo=False)

# initializes the database
Base.metadata.create_all(engine)

comment_counter = Counter()

def update_bio(user, content):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==user).first()
        user.bio = content
        session.commit()

def unmute_user(user):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==user).first()
        user.is_muted = False
        session.commit()

def mute_user(user):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==user).first()
        user.is_muted = True
        session.commit()

def remove_comment(article_id, comment_id):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.id==article_id).first()
        for comment in article.comments:
            if comment.id == comment_id:
                article.comments.remove(comment)
                session.commit()

def delete_article(article_id):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.id==article_id).first()
        session.delete(article)
        session.commit()

def update_article(article_id, title, content):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.id==article_id).first()
        article.title = title
        article.content = content
        session.commit()

def add_comment_to_article_by_title(article_title, comment, author):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.title==article_title).first()
        new_comment = Comment(content=comment, author=author, id=comment_counter.get())
        article.comments.append(new_comment)
        session.commit()

def get_article_by_id(id):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.id==id).first()
        return article
        
def get_article_by_title(title):
    with Session(engine) as session:
        article = session.query(Article).filter(Article.title==title).first()
        return article
        
def create_article(title, author, content):
    with Session(engine) as session:
        article = Article(title=title, author=author, content=content)
        session.add(article)
        session.commit()
        
def get_articles():
    with Session(engine) as session:
        articles = session.query(Article).all()
        return articles

def create_chatroom(id, members):
    with Session(engine) as session:
        chat_room = ChatRoom(id=id, members=members, message_history=[])
        session.add(chat_room)
        for member in members:
            user = session.query(User).filter(User.username==member).first()
            user.group_chats.update({id: members})
        session.commit()
        
def create_room(id, members):
    with Session(engine) as session:
        chat_room = ChatRoom(id=id, members=members, message_history=[])
        session.add(chat_room)
        session.commit()

def store_message(username, message, room_id):
    with Session(engine) as session:
        chat_room = session.query(ChatRoom).filter(ChatRoom.id==room_id).first()
        chat_room.message_history.append(f"{username}: {message}")
        session.commit()

def get_message_history(room_id):
    with Session(engine) as session:
        chat_room = session.query(ChatRoom).filter(ChatRoom.id==room_id).first()
        return chat_room.message_history
    
def get_chatrooms(username):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==username).first()
        return user.group_chats
    
# inserts a user to the database
def insert_user(username: str, password: str, salt: str, user_type: str):
    with Session(engine) as session:
        user = User(username=username, password=password, salt=salt, user_type=user_type)
        session.add(user)
        session.commit()

# gets a user from the database
def get_user(username: str):
    with Session(engine) as session:
        return session.get(User, username)
    
def get_friends(username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==username).first()
        return user.friends


# gets friend list from the database
def get_friends_list(username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==username).first()
        if user:
            friend_list = []
            for friend in user.friends:
                friend_to_add = session.query(User).filter(User.username==friend).first()
                friend_dict = {
                    "username": friend_to_add.username,
                    "user_type": friend_to_add.user_type
                }
                friend_list.append(friend_dict)
            return friend_list
        else:
            return None

# gets friend requests from the database
def get_friend_requests(username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==username).first()
        if user:
            return user.friend_requests
        else:
            return None

# gets outgoing friend requests from the database
def get_outgoing_friend_requests(username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username==username).first()
        if user:
            return user.outgoing_friend_requests
        else:
            return None

def remove_friend(username: str, friend_username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        if user:
            friend_to_remove = session.query(User).filter(User.username == friend_username).first()
            if friend_to_remove:
                user.friends.remove(friend_username)
                friend_to_remove.friends.remove(username)
                session.commit()
                

# sends friend request
def send_friend_request(username: str, friend_username: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        friend = session.query(User).filter(User.username == friend_username).first()
        if user and friend:
            if friend.username not in user.friends \
                and friend.username not in user.outgoing_friend_requests \
                    and friend.username not in user.friend_requests and \
                        friend.username != user.username:
                user.outgoing_friend_requests.append(friend.username)
                friend.friend_requests.append(user.username)
            else:
                if user == friend:
                    return 4
                return 2
            session.commit()
            return 1
        else:
            return 3

# accepts friend request
def accept_friend_request(username: str, friend_name: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        friend = session.query(User).filter(User.username == friend_name).first()
        if user and friend:
            if user.username not in friend.friends and friend.username not in user.friends:
                user.friends.append(friend.username)
                friend.friends.append(user.username)
                
                if friend_name in user.friend_requests:
                    user.friend_requests.remove(friend_name)
                if username in friend.outgoing_friend_requests:
                    friend.outgoing_friend_requests.remove(username)
                session.commit()
                return
    return

# reject friend request
def reject_friend_request(username: str, friend_name: str):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        friend = session.query(User).filter(User.username == friend_name).first()
        if user and friend:
            if friend_name in user.friend_requests:
                user.friend_requests.remove(friend_name)
            if username in friend.outgoing_friend_requests:
                friend.outgoing_friend_requests.remove(username)
            session.commit()
    return

# store message to database
# def store_message(username, friend, message):
#     with Session(engine) as session:
#         user = session.query(User).filter(User.username == username).first()
#         if user.message_history is None:
#             user.message_history = {}
#         if friend not in user.message_history:
#             user.message_history[friend] = []
#         previous_messages = user.message_history[friend]
#         updated_messages = previous_messages + [message]
#         user.message_history.update({friend: updated_messages})
#         session.commit()
#         return

# gets message history from database
# def get_message_history(username, friend):
#     with Session(engine) as session:
#         user = session.query(User).filter(User.username == username).first()
#         try:
#             return user.message_history[friend]
#         except KeyError:
#             return 'Key Error!'

# store public key to database
def store_key(username, public_key):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        user.public_key = public_key
        session.commit()
    return

# get public key from database
def get_public_key(username):
    with Session(engine) as session:
        user = session.query(User).filter(User.username == username).first()
        if user:
            return user.public_key
        else:
            return None
