'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''

from sqlalchemy import String, PickleType, Integer, Boolean
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Dict


# data models
class Base(DeclarativeBase):
    pass

# model to store user information
class User(Base):
    __tablename__ = "user"
    
    # data columns tied to each user
    username: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String)
    salt: Mapped[str] = mapped_column(String)
    user_type: Mapped[str] = mapped_column(String)
    public_key: Mapped[MutableDict] = mapped_column(MutableDict.as_mutable(PickleType), default={})
    friends: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])
    friend_requests: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])
    outgoing_friend_requests: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])
    group_chats: Mapped[MutableDict] = mapped_column(MutableDict.as_mutable(PickleType), default={})
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    bio: Mapped[str] = mapped_column(String, default=" ")
    
    
class ChatRoom(Base):
    __tablename__ = "chat_room"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    members: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])
    message_history: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])
    
class Article(Base):
    __tablename__ = "article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    comments: Mapped[MutableList] = mapped_column(MutableList.as_mutable(PickleType), default=[])


class Comment():    
    def __init__(self, content, author, id):
        self.content = content
        self.author = author
        self.id = id
        

# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        self.counter = 0
    
    def get(self):
        self.counter += 1
        return self.counter

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.rooms = {}

    def create_room(self, sender: str, receiver: str) -> int:
        room_id = self.counter.get()
        self.rooms[room_id] = [sender, receiver]
        return room_id
    
    def create_chatroom(self, members: list):
        room_id = self.counter.get()
        self.rooms[room_id] = members
        return room_id

    # gets the room id from a user
    def get_room_id(self, user1: str, user2: str):
        for room_id, users in self.rooms.items():
            if user1 in users and user2 in users:
                return room_id
        return None

