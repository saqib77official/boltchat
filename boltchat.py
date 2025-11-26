# boltchat.py - BoltChat v4.0 - Professional, Clean, One File, Ready to Deploy
import os
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, leave_room, emit
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ----------------------- Config -----------------------
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_FOLDER.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "chat.db"
SECRET_KEY = os.environ.get("CHAT_SECRET") or secrets.token_hex(16)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
socketio = SocketIO(app, cors_allowed_origins="*")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = declarative_base()
DBSession = sessionmaker(bind=engine)
db = DBSession()

# ----------------------- Models -----------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    online = Column(Boolean, default=False)
    sent_messages = relationship("Message", back_populates="sender")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", back_populates="sent_messages")

Base.metadata.create_all(engine)

# ----------------------- Helpers -----------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrapped

def current_user():
    if "user_id" not in session:
        return None
    return db.query(User).get(session["user_id"])

# ----------------------- HTML Templates -----------------------
HOME_HTML = """<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BoltChat - Professional Messaging</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .glass-nav { backdrop-filter: blur(20px); background: rgba(255,255,255,0.9); border-bottom: 1px solid rgba(139,92,246,0.2); }
    .btn-purple { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }
    .btn-purple:hover { background: linear-gradient(135deg, #7c3aed, #9333ea); transform: translateY(-2px); }
    .card-hover { transition: all 0.4s; }
    .card-hover:hover { transform: translateY(-12px); box-shadow: 0 25px 50px rgba(139,92,246,0.25); }
  </style>
</head>
<body class="bg-gradient-to-br from-purple-50 via-pink-50 to-purple-100 text-gray-900 min-h-screen">

  <!-- Navbar -->
  <nav class="fixed top-0 w-full glass-nav shadow-lg z-50">
    <div class="max-w-7xl mx-auto px-6 py-5 flex flex-col sm:flex-row justify-between items-center gap-4">
      <h1 class="text-3xl font-black bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">BoltChat</h1>
      <div class="flex flex-wrap gap-4 sm:gap-8 items-center text-lg">
        <a href="#features" class="hover:text-purple-600 font-medium transition">Features</a>
        <a href="#about" class="hover:text-purple-600 font-medium transition">About</a>
        {% if session.user_id %}
          <a href="/dashboard" class="px-8 py-3 btn-purple text-white rounded-full font-bold shadow-xl hover:shadow-2xl transition">Go to Chat</a>
        {% else %}
          <a href="/login" class="px-8 py-3 btn-purple text-white rounded-full font-bold shadow-xl hover:shadow-2xl transition">Login</a>
          <a href="/register" class="px-8 py-3 border-2 border-purple-400 text-purple-700 rounded-full font-bold hover:bg-purple-50 transition">Sign Up</a>
        {% endif %}
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="pt-32 pb-20 text-center px-6">
    <div class="max-w-5xl mx-auto">
      <h1 class="text-5xl sm:text-6xl md:text-7xl font-extrabold mb-6 leading-tight">
        Professional Real-Time<br>
        <span class="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Messaging</span>
      </h1>
      <p class="text-xl md:text-2xl text-gray-700 mb-12 max-w-3xl mx-auto opacity-90">
        Secure, fast, and reliable communication platform for teams and individuals.
      </p>
      <div class="flex flex-col sm:flex-row gap-6 justify-center max-w-md mx-auto">
        <a href="/register" class="px-10 py-5 btn-purple text-white text-xl font-bold rounded-full shadow-2xl hover:shadow-3xl transition card-hover">Get Started Free</a>
        <a href="#features" class="px-10 py-5 border-4 border-purple-400 text-purple-700 text-xl font-bold rounded-full hover:bg-purple-50 transition card-hover">Learn More</a>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section id="features" class="py-20 bg-white bg-opacity-60 backdrop-blur-sm">
    <div class="max-w-6xl mx-auto px-6 text-center">
      <h2 class="text-4xl md:text-5xl font-bold mb-16 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Why Choose BoltChat?</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-10">
        <div class="bg-white p-10 rounded-3xl shadow-xl border border-purple-100 text-center card-hover">
          <div class="w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <i class="fas fa-bolt text-3xl text-purple-600"></i>
          </div>
          <h3 class="text-2xl font-bold mb-4 text-gray-900">Instant Delivery</h3>
          <p class="text-gray-600">Real-time messaging with zero delay</p>
        </div>
        <div class="bg-white p-10 rounded-3xl shadow-xl border border-purple-100 text-center card-hover">
          <div class="w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <i class="fas fa-shield-alt text-3xl text-purple-600"></i>
          </div>
          <h3 class="text-2xl font-bold mb-4 text-gray-900">Secure & Private</h3>
          <p class="text-gray-600">Your conversations are protected</p>
        </div>
        <div class="bg-white p-10 rounded-3xl shadow-xl border border-purple-100 text-center card-hover">
          <div class="w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <i class="fas fa-mobile-alt text-3xl text-purple-600"></i>
          </div>
          <h3 class="text-2xl font-bold mb-4 text-gray-900">Mobile Ready</h3>
          <p class="text-gray-600">Perfect experience on any device</p>
        </div>
      </div>
    </div>
  </section>

  <!-- About Section -->
  <section id="about" class="py-20">
    <div class="max-w-6xl mx-auto px-6">
      <h2 class="text-4xl md:text-5xl font-bold text-center mb-16 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">About the Project</h2>
      <div class="grid md:grid-cols-2 gap-12 items-center">
        <div class="bg-white bg-opacity-80 backdrop-blur-lg p-10 rounded-3xl shadow-2xl border border-purple-100 text-center card-hover">
          <img src="https://media.licdn.com/dms/image/v2/D4D35AQGHe0O_GOIwvA/profile-framedphoto-shrink_400_400/B4DZg29uxYGgAc-/0/1753268809156?e=1764756000&v=beta&t=0iNBf6394oPwM2-m0HekM97NC0To0JYUOPpWepwIpbQ" 
               class="w-48 h-48 rounded-full mx-auto mb-6 border-8 border-purple-300 object-cover shadow-2xl" alt="Saqib Ullah">
          <h3 class="text-3xl font-bold text-gray-900">Saqib Ullah</h3>
          <p class="text-purple-600 font-bold text-xl mt-2">Founder & Lead Developer</p>
          <p class="mt-4 text-gray-700 text-lg">Full-Stack Developer | Real-Time Systems Expert</p>
        </div>
        <div class="space-y-6">
          <h3 class="text-4xl font-black bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">BOLTREACTOR</h3>
          <p class="text-xl text-gray-800 leading-relaxed">
            A professional technology initiative proudly affiliated with 
            <span class="text-purple-600 font-bold">KOMPASS TECHNOLOGIES PRIVATE LIMITED</span>
          </p>
          <p class="text-lg text-gray-700 leading-relaxed">
            We build clean, fast, and secure communication tools for the modern web.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-gradient-to-r from-purple-900 to-pink-900 text-white py-12 text-center">
    <p class="text-xl">&copy; 2025 <strong class="text-purple-300">BOLTREACTOR</strong> • Affiliated with KOMPASS TECHNOLOGIES PRIVATE LIMITED</p>
    <p class="text-sm opacity-80 mt-3">Built with passion by Saqib Ullah</p>
  </footer>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login • BoltChat</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
  <style>
    body { 
      font-family: 'Inter', sans-serif; 
      background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 35%, #d8b4fe 100%);
      min-height: 100vh;
    }
    .glass-card {
      background: rgba(255, 255, 255, 0.18);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.3);
      box-shadow: 0 15px 35px rgba(139, 92, 246, 0.25);
    }
    .input-glow:focus {
      box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.3);
    }
    .btn-purple {
      background: linear-gradient(135deg, #8b5cf6, #a78bfa);
      transition: all 0.3s;
    }
    .btn-purple:hover {
      background: linear-gradient(135deg, #7c3aed, #9333ea);
      transform: translateY(-3px);
      box-shadow: 0 15px 30px rgba(139, 92, 246, 0.4);
    }
  </style>
</head>
<body class="min-h-screen flex items-center justify-center px-4 py-10">
  <div class="w-full max-w-md">
    <div class="glass-card rounded-3xl p-10 shadow-2xl border border-white border-opacity-20">
      
      <!-- Logo / Title -->
      <div class="text-center mb-10">
        <h1 class="text-4xl md:text-5xl font-black bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
          BoltChat
        </h1>
        <p class="text-white text-xl mt-3 opacity-90">Welcome Back</p>
        <p class="text-white opacity-70 mt-1">Sign in to your account</p>
      </div>

      <!-- Error Message -->
      {% if error %}
        <div class="bg-red-500 bg-opacity-20 border border-red-400 text-white px-5 py-4 rounded-2xl mb-8 text-center font-medium">
          {{ error }}
        </div>
      {% endif %}

      <!-- Login Form -->
      <form method="POST" class="space-y-7">
        <div>
          <label class="block text-white text-sm font-semibold mb-3">Email Address</label>
          <input type="email" name="email" required 
                 class="w-full px-6 py-4 bg-white bg-opacity-20 border border-white border-opacity-40 rounded-2xl text-white placeholder-white placeholder-opacity-70 focus:outline-none focus:border-white input-glow transition"
                 placeholder="you@example.com">
        </div>
        
        <div>
          <label class="block text-white text-sm font-semibold mb-3">Password</label>
          <input type="password" name="password" required 
                 class="w-full px-6 py-4 bg-white bg-opacity-20 border border-white border-opacity-40 rounded-2xl text-white placeholder-white placeholder-opacity-70 focus:outline-none focus:border-white input-glow transition"
                 placeholder="••••••••">
        </div>

        <button type="submit" 
                class="w-full py-5 btn-purple text-white font-bold text-xl rounded-2xl shadow-xl hover:shadow-2xl transform hover:scale-105 transition">
          Sign In
        </button>
      </form>

      <!-- Sign Up Link -->
      <p class="text-center mt-10 text-white opacity-90 text-lg">
        Don't have an account? 
        <a href="/register" class="font-bold text-white underline hover:text-purple-200 transition">
          Sign up
        </a>
      </p>
    </div>

    <!-- Small credit -->
    <p class="text-center text-white opacity-60 mt-8 text-sm">
      © 2025 BOLTREACTOR • By Saqib Ullah
    </p>
  </div>
</body>
</html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sign Up • BoltChat</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
  <style>
    body { 
      font-family: 'Inter', sans-serif; 
      background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 35%, #d8b4fe 100%);
      min-height: 100vh;
    }
    .glass-card {
      background: rgba(255, 255, 255, 0.18);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.3);
      box-shadow: 0 15px 35px rgba(139, 92, 246, 0.25);
    }
    .input-glow:focus {
      box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.3);
    }
    .btn-purple {
      background: linear-gradient(135deg, #8b5cf6, #a78bfa);
      transition: all 0.3s;
    }
    .btn-purple:hover {
      background: linear-gradient(135deg, #7c3aed, #9333ea);
      transform: translateY(-3px);
      box-shadow: 0 15px 30px rgba(139, 92, 246, 0.4);
    }
  </style>
</head>
<body class="min-h-screen flex items-center justify-center px-4 py-10">
  <div class="w-full max-w-md">
    <div class="glass-card rounded-3xl p-10 shadow-2xl border border-white border-opacity-20">
      
      <!-- Logo / Title -->
      <div class="text-center mb-10">
        <h1 class="text-4xl md:text-5xl font-black bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
          BoltChat
        </h1>
        <p class="text-white text-xl mt-3 opacity-90">Create Account</p>
        <p class="text-white opacity-70 mt-1">Join BoltChat today</p>
      </div>

      <!-- Error Message -->
      {% if error %}
        <div class="bg-red-500 bg-opacity-20 border border-red-400 text-white px-5 py-4 rounded-2xl mb-8 text-center font-medium">
          {{ error }}
        </div>
      {% endif %}

      <!-- Register Form -->
      <form method="POST" class="space-y-7">
        <div>
          <label class="block text-white text-sm font-semibold mb-3">Full Name</label>
          <input type="text" name="name" required 
                 class="w-full px-6 py-4 bg-white bg-opacity-20 border border-white border-opacity-40 rounded-2xl text-white placeholder-white placeholder-opacity-70 focus:outline-none focus:border-white input-glow transition"
                 placeholder="Saqib Ullah">
        </div>
        
        <div>
          <label class="block text-white text-sm font-semibold mb-3">Email Address</label>
          <input type="email" name="email" required 
                 class="w-full px-6 py-4 bg-white bg-opacity-20 border border-white border-opacity-40 rounded-2xl text-white placeholder-white placeholder-opacity-70 focus:outline-none focus:border-white input-glow transition"
                 placeholder="you@example.com">
        </div>
        
        <div>
          <label class="block text-white text-sm font-semibold mb-3">Password</label>
          <input type="password" name="password" required 
                 class="w-full px-6 py-4 bg-white bg-opacity-20 border border-white border-opacity-40 rounded-2xl text-white placeholder-white placeholder-opacity-70 focus:outline-none focus:border-white input-glow transition"
                 placeholder="••••••••">
        </div>

        <button type="submit" 
                class="w-full py-5 btn-purple text-white font-bold text-xl rounded-2xl shadow-xl hover:shadow-2xl transform hover:scale-105 transition">
          Create Account
        </button>
      </form>

      <!-- Login Link -->
      <p class="text-center mt-10 text-white opacity-90 text-lg">
        Already have an account? 
        <a href="/login" class="font-bold text-white underline hover:text-purple-200 transition">
          Sign in
        </a>
      </p>
    </div>

    <!-- Credit -->
    <p class="text-center text-white opacity-60 mt-8 text-sm">
      © 2025 BOLTREACTOR • By Saqib Ullah
    </p>
  </div>
</body>
</html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BoltChat</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<style>
  body { font-family: 'Inter', sans-serif; font-size: 14px; }
  .glass-sidebar { 
    background: rgba(255, 255, 255, 0.92); 
    backdrop-filter: blur(20px); 
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(139, 92, 246, 0.2);
  }
  .online-dot { 
    @apply w-3 h-3 bg-green-500 rounded-full absolute bottom-0 right-0 border-2 border-white shadow-lg; 
  }
  .msg-time { font-size: 11px; opacity: 0.7; margin-top: 4px; }
  .input-glow:focus { 
    outline: none; 
    ring-4 ring-purple-400 ring-opacity-30; 
    border-color: #a78bfa; 
  }
</style>
</head>
<body class="h-full bg-gradient-to-br from-purple-50 via-pink-50 to-purple-100 flex flex-col md:flex-row">

  <!-- Mobile Header -->
  <div class="md:hidden bg-gradient-to-r from-purple-600 to-pink-600 text-white p-5 flex items-center justify-between shadow-2xl">
    <h1 class="text-2xl font-black">BoltChat</h1>
    <button onclick="toggleSidebar()" class="text-3xl"><i class="fas fa-bars"></i></button>
  </div>

  <!-- Sidebar -->
  <div id="sidebar" class="glass-sidebar w-full md:w-96 flex flex-col h-screen fixed md:relative z-50 transition-transform -translate-x-full md:translate-x-0 shadow-2xl">
    
    <!-- User Profile Header -->
    <div class="p-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <img src="{{ avatar_url }}" class="w-16 h-16 rounded-full ring-4 ring-white object-cover shadow-2xl">
          <div>
            <div class="font-bold text-xl">{{ name }}</div>
            <div class="text-sm opacity-90 flex items-center gap-2">
              <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span> Online
            </div>
          </div>
        </div>
        <div class="flex gap-3">
          <a href="/profile" class="p-3 bg-white bg-opacity-20 rounded-full hover:bg-opacity-40 transition"><i class="fas fa-user"></i></a>
          <a href="/logout" class="p-3 bg-white bg-opacity-20 rounded-full hover:bg-opacity-40 transition"><i class="fas fa-sign-out-alt"></i></a>
        </div>
      </div>
    </div>

    <!-- Global Room -->
    <div onclick="openRoom('global','Global Chat','/static/default-avatar.png',true)" 
         class="mx-5 mt-5 p-5 bg-gradient-to-r from-purple-100 to-pink-100 rounded-3xl cursor-pointer hover:shadow-xl transition transform hover:scale-105 flex items-center gap-4 border border-purple-200">
      <i class="fas fa-globe text-2xl text-purple-600"></i>
      <div>
        <div class="font-bold text-gray-900">Global Chat Room</div>
        <div class="text-xs text-purple-600">Public • Active now</div>
      </div>
    </div>

    <!-- Search -->
    <input type="text" id="searchUser" placeholder="Search users..." 
           class="mx-5 mt-5 px-5 py-4 bg-white bg-opacity-80 border-2 border-purple-200 rounded-3xl focus:border-purple-500 outline-none text-sm shadow-md input-glow transition">

    <!-- Users List -->
    <div id="users" class="flex-1 overflow-y-auto px-4 pb-6"></div>
  </div>

  <!-- Main Chat Area -->
  <div class="flex-1 flex flex-col h-screen">
    
    <!-- Chat Header -->
    <div class="bg-white bg-opacity-90 backdrop-blur-xl shadow-lg p-5 flex items-center gap-4 border-b border-purple-100">
      <button onclick="toggleSidebar()" class="md:hidden text-2xl text-purple-600"><i class="fas fa-arrow-left"></i></button>
      <img id="chatAvatar" src="/static/default-avatar.png" class="w-14 h-14 rounded-full ring-4 ring-purple-300 shadow-lg">
      <div>
        <div id="roomTitle" class="font-bold text-xl text-gray-800">Global Chat</div>
        <div id="chatStatus" class="text-sm text-purple-600 font-medium">Public room</div>
      </div>
    </div>

    <!-- Messages Area -->
    <div id="messages" class="flex-1 overflow-y-auto p-6 space-y-5 bg-gradient-to-b from-purple-50 to-pink-50"></div>

    <!-- Message Input -->
    <div class="p-5 bg-white bg-opacity-95 backdrop-blur-xl border-t-2 border-purple-200 shadow-2xl">
      <div class="flex gap-4 max-w-4xl mx-auto">
        <input id="msgInput" type="text" placeholder="Type a message..." 
               class="flex-1 px-6 py-4 bg-purple-50 bg-opacity-70 rounded-full focus:ring-4 focus:ring-purple-400 outline-none text-gray-800 font-medium input-glow transition shadow-inner"
               onkeydown="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()" 
                class="bg-gradient-to-r from-purple-600 to-pink-600 text-white w-16 h-16 rounded-full shadow-2xl hover:shadow-purple-500 hover:scale-110 transition flex items-center justify-center transform">
          <i class="fas fa-paper-plane text-xl"></i>
        </button>
      </div>
    </div>
  </div>

<script>
const socket = io();
const myId = {{ my_id }};
let currentRoom = "global";
let usersList = [];

if ("Notification" in window && Notification.permission === "default") {
  Notification.requestPermission();
}

socket.emit("join_room", { room: "global" });

socket.on("new_message", payload => {
  if (payload.room === currentRoom) appendMessage(payload);
  else if (Notification.permission === "granted") {
    new Notification(payload.sender_name, { 
      body: payload.content, 
      icon: payload.sender_avatar 
    });
  }
});

socket.on("online_users", data => { usersList = data; renderUsers(); });

async function fetchUsers() {
  const res = await fetch("/api/users");
  const json = await res.json();
  usersList = json.users;
  renderUsers();
}

function renderUsers() {
  const div = document.getElementById("users");
  div.innerHTML = "";
  const search = (document.getElementById("searchUser").value || "").toLowerCase();
  usersList
    .filter(u => u.id !== myId && u.name.toLowerCase().includes(search))
    .forEach(u => {
      const row = document.createElement("div");
      row.className = "flex items-center p-5 hover:bg-purple-50 rounded-2xl cursor-pointer border-b border-purple-100 transition my-2 shadow-sm";
      row.innerHTML = `
        <div class="relative">
          <img src="${u.avatar}" class="w-14 h-14 rounded-full object-cover ring-2 ring-purple-200 shadow-md">
          ${u.online ? '<div class="online-dot"></div>' : ''}
        </div>
        <div class="ml-4 flex-1">
          <div class="font-bold text-gray-800">${u.name}</div>
          <div class="text-xs ${u.online ? 'text-green-600' : 'text-gray-500'} font-medium">
            ${u.online ? 'Online' : 'Offline'}
          </div>
        </div>
      `;
      row.onclick = () => openRoom(u.id, u.name, u.avatar, u.online);
      div.appendChild(row);
    });
}

function openRoom(id, name, avatar, online) {
  const room = id === 'global' ? 'global' : "private_" + Math.min(id, myId) + "_" + Math.max(id, myId);
  socket.emit("leave_room", { room: currentRoom });
  currentRoom = room;
  document.getElementById("roomTitle").textContent = name;
  document.getElementById("chatAvatar").src = avatar || "/static/default-avatar.png";
  document.getElementById("chatStatus").textContent = online ? "Online" : "Offline";
  document.getElementById("messages").innerHTML = "";
  toggleSidebar();
  socket.emit("join_room", { room });
  fetch("/api/room_history?room=" + room).then(r => r.json()).then(d => d.messages.forEach(appendMessage));
}

function appendMessage(m) {
  const container = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = m.sender_id === myId ? "flex justify-end" : "flex justify-start";
  const time = new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  const bubble = m.sender_id === myId
    ? `<div class="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-4 rounded-3xl max-w-xs md:max-w-md shadow-lg">
         ${m.content}
         <div class="msg-time text-right">${time}</div>
       </div>`
    : `<div class="flex items-end gap-3 max-w-xs md:max-w-md">
         <img src="${m.sender_avatar}" class="w-10 h-10 rounded-full ring-2 ring-purple-200 shadow-md">
         <div class="bg-white px-6 py-4 rounded-3xl shadow-md border border-purple-100">
           <div class="text-xs font-bold text-purple-600">${m.sender_name}</div>
           ${m.content}
           <div class="msg-time text-gray-500">${time}</div>
         </div>
       </div>`;
  
  div.innerHTML = bubble;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function sendMessage() {
  const input = document.getElementById("msgInput");
  const text = input.value.trim();
  if (!text) return;
  socket.emit("send_message", { room: currentRoom, content: text });
  input.value = "";
}

function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("-translate-x-full");
}

fetchUsers();
setInterval(fetchUsers, 10000);
</script>
</body>
</html>"""

# ----------------------- Routes -----------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template_string(HOME_HTML)

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    avatar_url = url_for("uploaded_file", filename=user.avatar) if user.avatar else "/static/default-avatar.png"
    return render_template_string(DASHBOARD_HTML, name=user.name, my_id=user.id, avatar_url=avatar_url)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pwd = request.form.get("password", "")
        if not all([name, email, pwd]):
            return render_template_string(REGISTER_HTML, error="All fields are required.")
        if db.query(User).filter_by(email=email).first():
            return render_template_string(REGISTER_HTML, error="Email already registered.")
        user = User(name=name, email=email, password_hash=generate_password_hash(pwd))
        db.add(user); db.commit()
        session["user_id"] = user.id
        user.online = True; db.commit()
        return redirect("/dashboard")
    return render_template_string(REGISTER_HTML)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd = request.form.get("password", "")
        user = db.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, pwd):
            session["user_id"] = user.id
            user.online = True; db.commit()
            return redirect("/dashboard")
        return render_template_string(LOGIN_HTML, error="Invalid email or password.")
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
@login_required
def logout():
    user = current_user()
    if user:
        user.online = False
        db.commit()
    session.clear()
    return redirect("/")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        user.name = request.form.get("name", "").strip()
        file = request.files.get("avatar")
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"{user.id}_{secrets.token_hex(8)}.{ext}"
            file.save(UPLOAD_FOLDER / filename)
            user.avatar = filename
        db.commit()
    avatar_url = url_for("uploaded_file", filename=user.avatar) if user.avatar else "/static/default-avatar.png"
    return f'''<!DOCTYPE html>
<html><head><title>Profile</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
<div class="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
  <h2 class="text-2xl font-bold mb-6 text-center">Edit Profile</h2>
  <form method="POST" enctype="multipart/form-data" class="space-y-6">
    <img src="{avatar_url}" class="w-32 h-32 rounded-full mx-auto object-cover border-4 border-blue-600">
    <input type="text" name="name" value="{user.name}" required class="w-full p-4 border border-gray-300 rounded-lg">
    <input type="file" name="avatar" accept="image/*" class="w-full">
    <button class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700">Save Changes</button>
  </form>
  <a href="/dashboard" class="block text-center mt-6 text-blue-600 hover:underline">← Back to Chat</a>
</div>
</body></html>'''

@app.route("/api/users")
@login_required
def api_users():
    users = db.query(User).all()
    result = []
    for u in users:
        avatar = url_for("uploaded_file", filename=u.avatar) if u.avatar else "/static/default-avatar.png"
        result.append({"id": u.id, "name": u.name, "avatar": avatar, "online": u.online})
    return jsonify({"users": result})

@app.route("/api/room_history")
@login_required
def api_room_history():
    room = request.args.get("room", "global")
    msgs = db.query(Message).filter_by(room=room).order_by(Message.timestamp).limit(100).all()
    result = []
    for m in msgs:
        sender = db.query(User).get(m.sender_id)
        avatar = url_for("uploaded_file", filename=sender.avatar) if sender.avatar else "/static/default-avatar.png"
        result.append({
            "sender_id": m.sender_id,
            "sender_name": sender.name,
            "sender_avatar": avatar,
            "content": m.content,
            "timestamp": m.timestamp.isoformat()
        })
    return jsonify({"messages": result})

# ----------------------- SocketIO Events -----------------------
@socketio.on("join_room")
def handle_join(data):
    join_room(data["room"])

@socketio.on("leave_room")
def handle_leave(data):
    leave_room(data["room"])

@socketio.on("send_message")
def handle_message(data):
    sender = current_user()
    if not sender:
        return
    msg = Message(sender_id=sender.id, room=data["room"], content=data["content"])
    db.add(msg)
    db.commit()

    payload = {
        "sender_id": sender.id,
        "sender_name": sender.name,
        "sender_avatar": url_for("uploaded_file", filename=sender.avatar) if sender.avatar else "/static/default-avatar.png",
        "room": data["room"],
        "content": data["content"],
        "timestamp": msg.timestamp.isoformat()
    }
    emit("new_message", payload, to=data["room"])

    # Update online users
    users = []
    for u in db.query(User).all():
        avatar = url_for("uploaded_file", filename=u.avatar) if u.avatar else "/static/default-avatar.png"
        users.append({"id": u.id, "name": u.name, "avatar": avatar, "online": u.online})
    emit("online_users", users, broadcast=True)

# ----------------------- Default Avatar -----------------------
if not (STATIC_DIR / "default-avatar.png").exists():
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        draw.text((60, 70), "BC", fill="#2563eb", size=60)
        img.save(STATIC_DIR / "default-avatar.png")
    except:
        pass

# ----------------------- Run App -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)