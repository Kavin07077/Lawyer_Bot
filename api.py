"""
REST API Blueprint for LawyerBot
=================================
Base URL: /api/v1

Endpoints:
  POST   /api/v1/auth/register        - Register a new user
  POST   /api/v1/auth/login            - User login (returns token-style session)
  POST   /api/v1/auth/admin-login      - Admin login
  GET    /api/v1/auth/logout            - Logout

  POST   /api/v1/bot/query             - Send a query to the chatbot
  GET    /api/v1/sections              - List all IPC sections (paginated)
  GET    /api/v1/sections/search?q=    - Search IPC sections by keyword
  GET    /api/v1/sections/<id>         - Get a single section by ID

  GET    /api/v1/contacts              - List all lawyer contacts
  GET    /api/v1/contacts/search?district= - Search contacts by district
  GET    /api/v1/districts             - List distinct districts

  GET    /api/v1/users                 - List registered users (admin)
"""

from flask import Blueprint, request, jsonify, session
import mysql.connector
import re
import json
import os
from functools import wraps
from nltk.stem import PorterStemmer
from groq import Groq

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------
DB_CONFIG = dict(
    host="localhost",
    user="root",
    passwd="110707",
    charset="utf8",
    database="lawyerbot",
)


def get_db():
    """Return a fresh MySQL connection (short-lived, per-request pattern)."""
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# Groq LLM helper
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def ask_groq(user_question, db_context=""):
    """Call Groq LLM with the user's legal question and optional DB context."""
    if not groq_client:
        return "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable."
    system_prompt = (
        "You are an expert Indian legal assistant chatbot called LawyerBot. "
        "You help users understand Indian Penal Code (IPC) sections, offenses, "
        "and punishments. Answer clearly in simple language. "
        "If relevant IPC data is provided below, use it to give an accurate answer. "
        "If no data is provided or data is insufficient, answer from your own legal knowledge "
        "but mention that the user should consult a qualified lawyer for specific advice.\n\n"
    )
    if db_context:
        system_prompt += "Relevant IPC sections from the database:\n" + db_context + "\n"

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=1024,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API error: {e}")
        return "Sorry, I am unable to process your request right now. Please try again later."


# ---------------------------------------------------------------------------
# NLP helpers (same logic as main.py so results are consistent)
# ---------------------------------------------------------------------------
BASE_STOPWORDS = {
    word.strip()
    for word in """
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd she'll
she's should shouldn't so some such than that that's the their theirs them
themselves then there there's these they they'd they'll they're they've this
those through to too under until up very was wasn't we we'd we'll we're we've
were weren't what what's when when's where where's which while who who's whom why
why's with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves
""".split()
}

CUSTOM_STOPWORDS = {
    'rt', 'mkr', 'didn', 'bc', 'n', 'm', 'im', 'll', 'y', 've', 'u', 'ur',
    'don', 'p', 't', 's', 'aren', 'kp', 'o', 'kat', 'de', 're', 'amp', 'will',
}

TEXT_STOPWORDS = BASE_STOPWORDS.union(CUSTOM_STOPWORDS)
stemmer = PorterStemmer()


def clean_text(text: str) -> str:
    """NLP preprocessing identical to /bot route in main.py."""
    text = text.lower()
    text = re.sub(r"#[A-Za-z0-9_]+", ' ', text)
    text = re.sub(r'@\S+|https?:\S+|http?:\S|[^A-Za-z0-9]+', ' ', text)
    text = " ".join(w for w in text.split() if w not in TEXT_STOPWORDS)
    text = " ".join(stemmer.stem(w) for w in text.split())
    return text


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(f):
    """Decorator – rejects requests without an active session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator – rejects requests without an admin session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' not in session:
            return jsonify({"error": "Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated


# ===================================================================
#  AUTH  ENDPOINTS
# ===================================================================

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    """Register a new user.

    JSON body: {uname, name, mobile, email, location, password}
    """
    data = request.get_json(silent=True) or {}
    required = ['uname', 'name', 'mobile', 'email', 'location', 'password']
    missing = [f for f in required if f not in data or not data[f]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT count(*) FROM cc_register WHERE uname=%s", (data['uname'],))
        if cur.fetchone()[0] > 0:
            return jsonify({"error": "Username already exists."}), 409

        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM cc_register")
        new_id = cur.fetchone()[0]

        sql = ("INSERT INTO cc_register(id, name, mobile, email, location, uname, pass, otp, status) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
        cur.execute(sql, (new_id, data['name'], data['mobile'], data['email'],
                          data['location'], data['uname'], data['password'], '', '0'))
        db.commit()
        return jsonify({"message": "Registration successful.", "user_id": new_id}), 201
    finally:
        cur.close()
        db.close()


@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """User login.

    JSON body: {uname, password}
    """
    data = request.get_json(silent=True) or {}
    uname = data.get('uname', '')
    password = data.get('password', '')
    if not uname or not password:
        return jsonify({"error": "Username and password are required."}), 400

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT count(*) FROM cc_register WHERE uname=%s AND pass=%s", (uname, password))
        if cur.fetchone()[0] > 0:
            session['username'] = uname
            return jsonify({"message": "Login successful.", "username": uname}), 200
        return jsonify({"error": "Invalid credentials."}), 401
    finally:
        cur.close()
        db.close()


@api_bp.route('/auth/admin-login', methods=['POST'])
def api_admin_login():
    """Admin login.

    JSON body: {username, password}
    """
    data = request.get_json(silent=True) or {}
    uname = data.get('username', '')
    password = data.get('password', '')
    if not uname or not password:
        return jsonify({"error": "Username and password are required."}), 400

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("SELECT count(*) FROM cc_admin WHERE username=%s AND password=%s", (uname, password))
        if cur.fetchone()[0] > 0:
            session['admin'] = uname
            return jsonify({"message": "Admin login successful.", "username": uname}), 200
        return jsonify({"error": "Invalid admin credentials."}), 401
    finally:
        cur.close()
        db.close()


@api_bp.route('/auth/logout', methods=['GET'])
def api_logout():
    session.pop('username', None)
    session.pop('admin', None)
    return jsonify({"message": "Logged out."}), 200


# ===================================================================
#  BOT / CHAT  ENDPOINT
# ===================================================================

@api_bp.route('/bot/query', methods=['POST'])
@login_required
def api_bot_query():
    """Send a question to the chatbot.

    JSON body: {message: "your legal question", language: "" }
    language is optional (e.g. "ta", "hi", "ml").
    Returns: {answer: "...", sections: [...]}
    """
    data = request.get_json(silent=True) or {}
    msg_input = data.get('message', '').strip()

    if not msg_input or msg_input.lower() == 'hi':
        return jsonify({"answer": "How can I help you?", "sections": []}), 200

    cleaned = clean_text(msg_input)
    like_cleaned = f'%{cleaned}%'
    like_raw = f'%{msg_input}%'

    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        # Try cleaned text first
        cur.execute(
            "SELECT count(*) AS cnt FROM cc_data "
            "WHERE user_query LIKE %s OR offense LIKE %s OR description LIKE %s",
            (like_cleaned, like_cleaned, like_cleaned),
        )
        use_cleaned = cur.fetchone()['cnt'] > 0
        like_param = like_cleaned if use_cleaned else like_raw

        cur.execute(
            "SELECT * FROM cc_data "
            "WHERE user_query LIKE %s OR offense LIKE %s OR description LIKE %s "
            "LIMIT 5",
            (like_param, like_param, like_param),
        )
        rows = cur.fetchall()

        sections = []
        db_context = ""
        for r in rows:
            sections.append({
                "id": r['id'],
                "section": r.get('section', ''),
                "description": r.get('description', ''),
                "offense": r.get('offense', ''),
                "punishment": r.get('punishment', ''),
            })
            db_context += f"\nIPC Section: {r.get('section', '')}\n"
            db_context += f"Description: {r.get('description', '')}\n"
            if r.get('offense'):
                db_context += f"Offense: {r['offense']}\n"
            if r.get('punishment'):
                db_context += f"Punishment: {r['punishment']}\n"

        # Call Groq LLM for an AI-powered explanation
        ai_response = ask_groq(msg_input, db_context)

        # Gather available districts
        cur.execute("SELECT DISTINCT district FROM cc_contact")
        districts = [row['district'] for row in cur.fetchall()]

        return jsonify({
            "answer": ai_response,
            "sections": sections,
            "available_districts": districts,
        }), 200

    finally:
        cur.close()
        db.close()


# ===================================================================
#  IPC  SECTIONS  ENDPOINTS
# ===================================================================

@api_bp.route('/sections', methods=['GET'])
def api_list_sections():
    """List all IPC sections (paginated).

    Query params: page (default 1), per_page (default 20)
    """
    page = max(int(request.args.get('page', 1)), 1)
    per_page = min(int(request.args.get('per_page', 20)), 100)
    offset = (page - 1) * per_page

    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT count(*) AS total FROM cc_data")
        total = cur.fetchone()['total']

        cur.execute("SELECT * FROM cc_data ORDER BY id LIMIT %s OFFSET %s", (per_page, offset))
        rows = cur.fetchall()

        sections = []
        for r in rows:
            sections.append({
                "id": r['id'],
                "section": r.get('section', ''),
                "description": r.get('description', ''),
                "offense": r.get('offense', ''),
                "punishment": r.get('punishment', ''),
            })

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "sections": sections,
        }), 200
    finally:
        cur.close()
        db.close()


@api_bp.route('/sections/search', methods=['GET'])
def api_search_sections():
    """Search IPC sections by keyword.

    Query params: q (search term), page, per_page
    """
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required."}), 400

    page = max(int(request.args.get('page', 1)), 1)
    per_page = min(int(request.args.get('per_page', 20)), 100)
    offset = (page - 1) * per_page

    cleaned = clean_text(q)
    like_param = f'%{cleaned}%'
    like_raw = f'%{q}%'

    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        # Count with cleaned text
        cur.execute(
            "SELECT count(*) AS cnt FROM cc_data "
            "WHERE user_query LIKE %s OR offense LIKE %s OR description LIKE %s OR section LIKE %s",
            (like_param, like_param, like_param, like_param),
        )
        cnt = cur.fetchone()['cnt']
        if cnt == 0:
            like_param = like_raw
            cur.execute(
                "SELECT count(*) AS cnt FROM cc_data "
                "WHERE user_query LIKE %s OR offense LIKE %s OR description LIKE %s OR section LIKE %s",
                (like_param, like_param, like_param, like_param),
            )
            cnt = cur.fetchone()['cnt']

        cur.execute(
            "SELECT * FROM cc_data "
            "WHERE user_query LIKE %s OR offense LIKE %s OR description LIKE %s OR section LIKE %s "
            "ORDER BY id LIMIT %s OFFSET %s",
            (like_param, like_param, like_param, like_param, per_page, offset),
        )
        rows = cur.fetchall()

        sections = []
        for r in rows:
            sections.append({
                "id": r['id'],
                "section": r.get('section', ''),
                "description": r.get('description', ''),
                "offense": r.get('offense', ''),
                "punishment": r.get('punishment', ''),
            })

        return jsonify({"total": cnt, "page": page, "per_page": per_page, "sections": sections}), 200
    finally:
        cur.close()
        db.close()


@api_bp.route('/sections/<int:section_id>', methods=['GET'])
def api_get_section(section_id):
    """Get a single IPC section by its ID."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM cc_data WHERE id=%s", (section_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Section not found."}), 404
        return jsonify({
            "id": row['id'],
            "section": row.get('section', ''),
            "description": row.get('description', ''),
            "offense": row.get('offense', ''),
            "punishment": row.get('punishment', ''),
        }), 200
    finally:
        cur.close()
        db.close()


# ===================================================================
#  CONTACTS / DISTRICTS  ENDPOINTS
# ===================================================================

@api_bp.route('/contacts', methods=['GET'])
def api_list_contacts():
    """List all lawyer contacts."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM cc_contact ORDER BY id")
        rows = cur.fetchall()
        contacts = []
        for r in rows:
            contacts.append({
                "id": r['id'],
                "section_id": r.get('section_id', ''),
                "district": r.get('district', ''),
                "name": r.get('name', ''),
                "mobile": r.get('mobile', ''),
                "email": r.get('email', ''),
                "address": r.get('address', ''),
            })
        return jsonify({"total": len(contacts), "contacts": contacts}), 200
    finally:
        cur.close()
        db.close()


@api_bp.route('/contacts/search', methods=['GET'])
def api_search_contacts():
    """Search lawyer contacts by district.

    Query params: district
    """
    district = request.args.get('district', '').strip()
    if not district:
        return jsonify({"error": "Query parameter 'district' is required."}), 400

    like_param = f'%{district}%'

    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM cc_contact WHERE district LIKE %s ORDER BY id", (like_param,))
        rows = cur.fetchall()
        contacts = []
        for r in rows:
            contacts.append({
                "id": r['id'],
                "section_id": r.get('section_id', ''),
                "district": r.get('district', ''),
                "name": r.get('name', ''),
                "mobile": r.get('mobile', ''),
                "email": r.get('email', ''),
                "address": r.get('address', ''),
            })
        return jsonify({"total": len(contacts), "contacts": contacts}), 200
    finally:
        cur.close()
        db.close()


@api_bp.route('/districts', methods=['GET'])
def api_list_districts():
    """List all distinct districts that have lawyer contacts."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT DISTINCT district FROM cc_contact ORDER BY district")
        rows = cur.fetchall()
        districts = [r['district'] for r in rows]
        return jsonify({"districts": districts}), 200
    finally:
        cur.close()
        db.close()


# ===================================================================
#  USERS  ENDPOINT  (admin only)
# ===================================================================

@api_bp.route('/users', methods=['GET'])
@admin_required
def api_list_users():
    """List all registered users (admin only)."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, mobile, email, location, uname, status FROM cc_register")
        rows = cur.fetchall()
        return jsonify({"total": len(rows), "users": rows}), 200
    finally:
        cur.close()
        db.close()
