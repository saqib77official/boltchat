import os
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey

from flask import Flask, request, redirect, url_for, render_template_string, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, leave_room, emit
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# -----------------------
# Config
# -----------------------
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "chat.db"
SECRET_KEY = os.environ.get("CHAT_SECRET") or secrets.token_hex(16)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

# -----------------------
# Flask & SocketIO
# -----------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
socketio = SocketIO(app, cors_allowed_origins="*")

# -----------------------
# Database
# -----------------------
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
db = DBSession()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    online = Column(Boolean, default=False)
    # Correct relationship
    sent_messages = relationship("Message", back_populates="sender")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # <-- add ForeignKey here
    room = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", back_populates="sent_messages")


Base.metadata.create_all(engine)

# -----------------------
# Helpers
# -----------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def current_user():
    if "user_id" not in session:
        return None
    return db.query(User).filter_by(id=session["user_id"]).first()

def private_room_name(a_id, b_id):
    a, b = sorted([int(a_id), int(b_id)])
    return f"private_{a}_{b}"

# -----------------------
# Routes
# -----------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -----------------------
# Login/Signup/Profile Templates
# -----------------------
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Login - Chat App</title>
<style>
body{background:#f0f2f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 25px rgba(0,0,0,0.1);width:360px;text-align:center}
h2{margin-bottom:20px;color:#00a8ff}input{width:100%;padding:12px 15px;margin:10px 0;border-radius:8px;border:1px solid #ccc;outline:none}
button{width:100%;padding:12px;background:#00a8ff;border:none;border-radius:8px;color:white;font-weight:bold;cursor:pointer;transition:.2s}
button:hover{background:#0097e6}.error{color:red;margin-bottom:10px;font-size:14px}.bottom{text-align:center;margin-top:15px;font-size:14px}
.bottom a{color:#00a8ff;text-decoration:none}
</style>
</head>
<body>
<div class="box">
<h2>Login</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST">
<input type="email" name="email" placeholder="Email" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
<div class="bottom">Don't have an account? <a href="{{ url_for('register') }}">Sign Up</a></div>
</div>
</body>
</html>
"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sign Up - Chat App</title>
<style>
body{background:#f0f2f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 25px rgba(0,0,0,0.1);width:360px;text-align:center}
h2{margin-bottom:20px;color:#00a8ff}input{width:100%;padding:12px 15px;margin:10px 0;border-radius:8px;border:1px solid #ccc;outline:none}
button{width:100%;padding:12px;background:#00a8ff;border:none;border-radius:8px;color:white;font-weight:bold;cursor:pointer;transition:.2s}
button:hover{background:#0097e6}.error{color:red;margin-bottom:10px;font-size:14px}.bottom{text-align:center;margin-top:15px;font-size:14px}
.bottom a{color:#00a8ff;text-decoration:none}
</style>
</head>
<body>
<div class="box">
<h2>Create Account</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST">
<input type="text" name="name" placeholder="Full Name" required>
<input type="email" name="email" placeholder="Email" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Sign Up</button>
</form>
<div class="bottom">Already have an account? <a href="{{ url_for('login') }}">Login</a></div>
</div>
</body>
</html>
"""

PROFILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Edit Profile - Chat App</title>
<style>
body{background:#f0f2f5;font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 25px rgba(0,0,0,0.1);width:400px;text-align:center}
h2{color:#00a8ff;margin-bottom:20px}input[type=text],input[type=file]{width:100%;padding:12px 15px;margin:10px 0;border-radius:8px;border:1px solid #ccc}
button{width:100%;padding:12px;background:#00a8ff;border:none;border-radius:8px;color:white;font-weight:bold;cursor:pointer;transition:.2s}
button:hover{background:#0097e6}img{width:100px;height:100px;border-radius:50%;margin-bottom:10px;object-fit:cover;border:2px solid #00a8ff}
a{text-decoration:none;color:#00a8ff;display:block;margin-top:10px}
</style>
</head>
<body>
<div class="box">
<h2>Edit Profile</h2>
<form method="POST" enctype="multipart/form-data">
<img src="{{ avatar_url }}" alt="avatar">
<input type="text" name="name" value="{{ name }}" placeholder="Your Name" required>
<input type="file" name="avatar" accept="image/*">
<button type="submit">Save Changes</button>
</form>
<a href="{{ url_for('index') }}">Back to Chat</a>
</div>
</body>
</html>
"""

# -----------------------
# Dashboard (modern WhatsApp style)
# -----------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Chat Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}body,html{height:100%;font-family:'Segoe UI',sans-serif}  
.container{display:flex;height:100vh;background:#f0f2f5}  
.sidebar{width:300px;background:#2f3640;color:#f5f6fa;display:flex;flex-direction:column}  
.sidebar .top{padding:15px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #404857}  
.sidebar .top img{width:40px;height:40px;border-radius:50%;object-fit:cover}  
.sidebar .top .name{flex:1;font-weight:bold}  
.sidebar .top button{margin-left:5px;padding:5px 10px;border:none;border-radius:8px;background:#00a8ff;color:white;cursor:pointer}  
.sidebar input{margin:10px;padding:8px;border-radius:8px;border:none}  
.sidebar .users{flex:1;overflow-y:auto}  
.user-row{display:flex;align-items:center;padding:8px 12px;cursor:pointer;border-bottom:1px solid #404857;transition:.2s}  
.user-row:hover{background:#414b57}  
.user-row img{width:35px;height:35px;border-radius:50%;margin-right:10px}  
.user-row .status{margin-left:auto;font-size:12px;color:#4cd137}  

.chat{flex:1;display:flex;flex-direction:column;background:#dcdde1}  
.chat .topbar{padding:15px;background:#00a8ff;color:white;font-weight:bold;font-size:18px;display:flex;justify-content:space-between;align-items:center}  
.chat .messages{flex:1;padding:15px;overflow-y:auto;background:#f5f6fa;display:flex;flex-direction:column}  
.messages .msg{margin-bottom:12px;max-width:70%;padding:10px 15px;border-radius:20px;position:relative;display:inline-block}  
.messages .msg.me{background:#00a8ff;color:white;align-self:flex-end;border-bottom-right-radius:0}  
.messages .msg.other{background:#f1f2f6;color:#2f3640;align-self:flex-start;border-bottom-left-radius:0;display:flex;align-items:flex-end}  
.messages .msg.other img{width:25px;height:25px;border-radius:50%;margin-right:5px;object-fit:cover}  
.messages .msg .meta{font-size:10px;color:#999;margin-top:4px}  

.composer{display:flex;padding:12px;border-top:1px solid #ccc;background:#f5f6fa}  
.composer input{flex:1;padding:10px 15px;border-radius:25px;border:1px solid #ccc;outline:none;margin-right:10px}  
.composer button{padding:10px 20px;border:none;border-radius:25px;background:#00a8ff;color:white;font-weight:bold;cursor:pointer;transition:.2s}  
.composer button:hover{background:#0097e6}
</style>
</head>
<body>
<div class="container">
<div class="sidebar">
  <div class="top">
    <img id="myAvatar" src="{{ avatar_url }}">
    <div class="name">{{ name }}</div>
    <button onclick="window.location.href='{{ url_for('profile') }}'">Edit</button>
    <button onclick="window.location.href='{{ url_for('logout') }}'">Logout</button>
  </div>
  <input type="text" id="searchUser" placeholder="Search users..." oninput="filterUsers()">
  <div class="users" id="users"></div>
</div>
<div class="chat">
  <div class="topbar" id="roomTitle">Global Chat</div>
  <div class="messages" id="messages"></div>
  <div class="composer">
    <input id="msgInput" type="text" placeholder="Type a message..." autocomplete="off">
    <button onclick="sendMessage()">Send</button>
  </div>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
const socket = io();const myId={{ my_id }};let currentRoom="global";let currentRoomName="Global Chat";let usersList=[];
socket.emit("join_room",{room:"global"});

socket.on("new_message",payload=>{if(payload.room===currentRoom)appendMessage(payload);});
socket.on("online_users",data=>{usersList=data;renderUsers();});

async function fetchUsers(){let res=await fetch("/api/users");let data=await res.json();usersList=data.users;renderUsers();}
function renderUsers(){let div=document.getElementById("users");div.innerHTML="";let search=document.getElementById("searchUser").value.toLowerCase();usersList.forEach(u=>{if(u.id===myId||!u.name.toLowerCase().includes(search))return;let row=document.createElement("div");row.className="user-row";row.innerHTML=`<img src="${u.avatar}"><span>${u.name}</span>${u.online?'<span class="status">●</span>':''}`;row.onclick=()=>openRoom(u.id,u.name);div.appendChild(row);});}
function filterUsers(){renderUsers();}

async function openRoom(userId,label){const room="private_"+Math.min(userId,myId)+"_"+Math.max(userId,myId);socket.emit("leave_room",{room:currentRoom});currentRoom=room;currentRoomName=label;document.getElementById("roomTitle").textContent=label;document.getElementById("messages").innerHTML="";socket.emit("join_room",{room});const res=await fetch("/api/room_history?room="+encodeURIComponent(room));const data=await res.json();data.messages.forEach(appendMessage);}
function appendMessage(m){const container=document.getElementById("messages");const div=document.createElement("div");div.className="msg "+(m.sender_id===myId?"me":"other");if(m.sender_id!==myId){div.innerHTML=`<img src="${m.sender_avatar}">${m.content}<div class="meta">${m.sender_name} • ${new Date(m.timestamp).toLocaleTimeString()}</div>`;}else{div.innerHTML=`${m.content}<div class="meta">${m.sender_name} • ${new Date(m.timestamp).toLocaleTimeString()}</div>`;}container.appendChild(div);container.scrollTop=container.scrollHeight;}
function sendMessage(){const text=document.getElementById("msgInput").value.trim();if(!text)return;socket.emit("send_message",{room:currentRoom,content:text});document.getElementById("msgInput").value="";}
fetchUsers();setInterval(fetchUsers,8000);
</script>
</body>
</html>
"""

# -----------------------
# Flask routes
# -----------------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        pwd=request.form.get("password","")
        if not name or not email or not pwd:
            return render_template_string(REGISTER_HTML,error="All fields required.")
        if db.query(User).filter_by(email=email).first():
            return render_template_string(REGISTER_HTML,error="Email already registered.")
        user=User(name=name,email=email,password_hash=generate_password_hash(pwd))
        db.add(user); db.commit()
        session["user_id"]=user.id;user.online=True;db.commit()
        return redirect(url_for("index"))
    return render_template_string(REGISTER_HTML)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        pwd=request.form.get("password","")
        user=db.query(User).filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash,pwd):
            return render_template_string(LOGIN_HTML,error="Invalid credentials.")
        session["user_id"]=user.id;user.online=True;db.commit()
        return redirect(url_for("index"))
    return render_template_string(LOGIN_HTML,error=None)

@app.route("/logout")
@login_required
def logout():
    u=current_user()
    if u: u.online=False; db.commit()
    session.clear()
    return redirect(url_for("login"))

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    u=current_user()
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if name:u.name=name
        if "avatar" in request.files:
            f=request.files["avatar"]
            if f and allowed_file(f.filename):
                filename=secure_filename(f.filename)
                filename=f"{u.id}_{secrets.token_hex(6)}_{filename}"
                f.save(Path(app.config["UPLOAD_FOLDER"])/filename)
                u.avatar=filename
        db.commit()
        return redirect(url_for("profile"))
    avatar_url=url_for("uploaded_file",filename=u.avatar) if u.avatar else url_for("static",filename="default-avatar.png")
    return render_template_string(PROFILE_HTML,name=u.name,avatar_url=avatar_url)

@app.route("/")
@login_required
def index():
    u=current_user()
    avatar_url=url_for("uploaded_file",filename=u.avatar) if u.avatar else url_for("static",filename="default-avatar.png")
    return render_template_string(INDEX_HTML,name=u.name,my_id=u.id,avatar_url=avatar_url)

@app.route("/api/users")
@login_required
def api_users():
    users=db.query(User).all()
    result=[]
    for u in users:
        avatar_url=url_for("uploaded_file",filename=u.avatar) if u.avatar else url_for("static",filename="default-avatar.png")
        result.append({"id":u.id,"name":u.name,"avatar":avatar_url,"online":u.online})
    return jsonify({"users":result})

@app.route("/api/room_history")
@login_required
def api_room_history():
    room=request.args.get("room")
    msgs=db.query(Message).filter_by(room=room).order_by(Message.timestamp.asc()).all()
    result=[]
    for m in msgs:
        sender=db.query(User).filter_by(id=m.sender_id).first()
        result.append({"sender_id":m.sender_id,"sender_name":sender.name,"sender_avatar":url_for("uploaded_file",filename=sender.avatar) if sender.avatar else url_for("static",filename="default-avatar.png"),"content":m.content,"timestamp":m.timestamp.isoformat()})
    return jsonify({"messages":result})

# -----------------------
# SocketIO Events
# -----------------------
@socketio.on("join_room")
def handle_join(data):
    join_room(data["room"])

@socketio.on("leave_room")
def handle_leave(data):
    leave_room(data["room"])

@socketio.on("send_message")
def handle_message(data):
    sender=current_user()
    room=data["room"]
    content=data["content"]
    msg=Message(sender_id=sender.id,room=room,content=content)
    db.add(msg); db.commit()
    payload={"sender_id":sender.id,"sender_name":sender.name,"sender_avatar":url_for("uploaded_file",filename=sender.avatar) if sender.avatar else url_for("static",filename="default-avatar.png"),"room":room,"content":content,"timestamp":msg.timestamp.isoformat()}
    emit("new_message",payload,to=room)
    # Update online users for live status
    users=[{"id":u.id,"name":u.name,"avatar":url_for("uploaded_file",filename=u.avatar) if u.avatar else url_for("static",filename="default-avatar.png"),"online":u.online} for u in db.query(User).all()]
    emit("online_users",users,broadcast=True)

# -----------------------
# Static default avatar
# -----------------------
STATIC_DIR=BASE_DIR/"static"
STATIC_DIR.mkdir(exist_ok=True)
default_avatar=STATIC_DIR/"default-avatar.png"
if not default_avatar.exists():
    from PIL import Image, ImageDraw
    im=Image.new("RGB",(100,100),(200,200,200))
    d=ImageDraw.Draw(im);d.text((25,40),"U",(255,255,255))
    im.save(default_avatar)

# -----------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port or 5000 locally
    socketio.run(app, host="0.0.0.0", port=port, debug=False)

