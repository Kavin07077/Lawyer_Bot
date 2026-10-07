from flask import Flask
from flask import Flask, render_template, Response, redirect, request, session, abort, url_for
import os
import base64
from PIL import Image
from datetime import datetime
from datetime import date
import datetime
import random
from random import seed
from random import randint
import re
import cv2
import PIL.Image
from PIL import Image
from flask import send_file
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv
import threading
import time
import shutil
import hashlib
import urllib.request
import urllib.parse
from urllib.request import urlopen
import webbrowser
import json
import mysql.connector
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import urllib.request
import urllib.parse


from nltk.stem import PorterStemmer
from groq import Groq


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
    'rt', 'mkr', 'didn', 'bc', 'n', 'm', 'im', 'll', 'y', 've', 'u', 'ur', 'don',
    'p', 't', 's', 'aren', 'kp', 'o', 'kat', 'de', 're', 'amp', 'will'
}

TEXT_STOPWORDS = BASE_STOPWORDS.union(CUSTOM_STOPWORDS)
#from keras.layers import Input, Dense, LSTM, TimeDistributed
#import spacy
#nlp = spacy.load('en')

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="110707",
    charset="utf8",
    database="lawyerbot"
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
##session key
app.secret_key = 'abcdef'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'upload')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DET_FILE = os.path.join(BASE_DIR, 'static', 'det.txt')

# Add built-in functions to Jinja2 templates
app.jinja_env.globals.update(int=int, range=range, len=len, str=str)

# ---------- Groq LLM ----------
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def ask_groq(user_question, db_context=""):
    """Send the user's legal question to Groq LLM along with relevant DB context."""
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
# --------------------------------

# ---------- REST API Blueprint ----------
from api import api_bp
app.register_blueprint(api_bp)
# ----------------------------------------
#####

@app.route('/',methods=['POST','GET'])
def index():
    msg=""
    mycursor = mydb.cursor()
    if request.method == 'POST':
        
        username1 = request.form['uname']
        password1 = request.form['pass']
        mycursor = mydb.cursor()
        mycursor.execute("SELECT count(*) FROM cc_register where uname=%s && pass=%s",(username1,password1))
        myresult = mycursor.fetchone()[0]
        if myresult>0:
            session['username'] = username1
            #result=" Your Logged in sucessfully**"
            return redirect(url_for('bot')) 
        else:
            msg="You are logged in fail!!!"

    return render_template('index.html',msg=msg)

@app.route('/login',methods=['POST','GET'])
def login():
    cnt=0
    act=""
    msg=""
    if request.method == 'POST':
        
        username1 = request.form['uname']
        password1 = request.form['pass']
        mycursor = mydb.cursor()
        mycursor.execute("SELECT count(*) FROM cc_admin where username=%s && password=%s",(username1,password1))
        myresult = mycursor.fetchone()[0]
        if myresult>0:
            session['username'] = username1
            #result=" Your Logged in sucessfully**"
            return redirect(url_for('admin')) 
        else:
            msg="You are logged in fail!!!"
        

    return render_template('login.html',msg=msg,act=act)

@app.route('/login_user',methods=['POST','GET'])
def login_user():
    cnt=0
    act=""
    msg=""
    if request.method == 'POST':
        
        username1 = request.form['uname']
        password1 = request.form['pass']
        mycursor = mydb.cursor()
        mycursor.execute("SELECT count(*) FROM cc_register where uname=%s && pass=%s",(username1,password1))
        myresult = mycursor.fetchone()[0]
        if myresult>0:
            session['username'] = username1
            #result=" Your Logged in sucessfully**"
            return redirect(url_for('bot')) 
        else:
            msg="You are logged in fail!!!"
        

    return render_template('login_user.html',msg=msg,act=act)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    msg=""
    mycursor = mydb.cursor()
    if request.method=='POST':
        file = request.files['file']

        fn="datafile.csv"
        file.save(os.path.join(UPLOAD_FOLDER, fn))

        filename = os.path.join(UPLOAD_FOLDER, 'datafile.csv')
        data1 = pd.read_csv(filename, header=0)
        data2 = list(data1.values.flatten())
        for ss in data1.values:
            val1=""
            if pd.isnull(ss[1]):
                val1=""
            else:
                val1=ss[1]
                
            val2=""
            if pd.isnull(ss[2]):
                val2=""
            else:
                val2=ss[2]
                
            val3=""
            if pd.isnull(ss[3]):
                val3=""
            else:
                val3=ss[3]

            
                
            mycursor.execute("SELECT max(id)+1 FROM cc_data")
            maxid = mycursor.fetchone()[0]
            if maxid is None:
                maxid=1

            sql = "INSERT INTO cc_data(id,description,offense,punishment,section) VALUES (%s,%s,%s,%s,%s)"
            val = (maxid,ss[0],val1,val2,val3)
            mycursor.execute(sql, val)

        mydb.commit()
        
        msg="success"
        
    return render_template('admin.html',msg=msg)

@app.route('/process', methods=['GET', 'POST'])
def process():
    msg=""
    cnt=0
    

    filename = os.path.join(UPLOAD_FOLDER, 'datafile.csv')
    data1 = pd.read_csv(filename, header=0)
    data2 = list(data1.values.flatten())

    
    data=[]
    i=0
    sd=len(data1)
    rows=len(data1.values)
    
    #print(str(sd)+" "+str(rows))
    for ss in data1.values:
        cnt=len(ss)
        data.append(ss)
    cols=cnt

    
    return render_template('process.html',data=data, msg=msg, rows=rows, cols=cols)

@app.route('/process2', methods=['GET', 'POST'])
def process2():
    msg=""
    act=request.args.get("act")
    
    return render_template('process2.html',msg=msg, act=act)

@app.route('/add_query', methods=['GET', 'POST'])
def add_query():
    msg=""
    sid=""
    mycursor = mydb.cursor()

    cnt=0
    
    data=[]
    

    mycursor.execute("SELECT * FROM cc_data")
    data = mycursor.fetchall()
        
    
    if request.method=='POST':
        sid=request.form['sid']
        
        msg="success"

    return render_template('add_query.html',msg=msg,sid=sid,data=data)


@app.route('/add_query1', methods=['GET', 'POST'])
def add_query1():
    msg=""
    act=request.args.get("act")
    sid=request.args.get("sid")
    mycursor = mydb.cursor()
    
    cnt=0
    #filename = 'static/upload/datafile.csv'
    #data1 = pd.read_csv(filename, header=0,encoding='cp1252')
    #data2 = list(data1.values.flatten())

    
    data=[]
    #i=0
    #for ss in data1.values:
    #    cnt=len(ss)
    #    data.append(ss)
    #cols=cnt

    mycursor.execute("SELECT * FROM cc_data where id=%s",(sid,))
    data = mycursor.fetchone()

    mycursor.execute("SELECT * FROM cc_contact")
    data2 = mycursor.fetchall()
        
    
    if request.method=='POST':
        
        user_query=request.form['user_query']
        district=request.form['district']
        name=request.form['name']
        mobile=request.form['mobile']
        email=request.form['email']
        address=request.form['address']
        
        
        mycursor.execute("update cc_data set user_query=%s,district=%s,name=%s,mobile=%s,email=%s,address=%s where id=%s",(user_query,district,name,mobile,email,address,sid))
        mydb.commit()

        mycursor.execute("SELECT count(*) FROM cc_contact where id=%s && name=%s && mobile=%s",(sid,name,mobile))
        d1 = mycursor.fetchone()[0]
        if d1==0:
            mycursor.execute("SELECT max(id)+1 FROM cc_contact")
            maxid = mycursor.fetchone()[0]
            if maxid is None:
                maxid=1

            

            sql = "INSERT INTO cc_contact(id,section_id,district,name,mobile,email,address) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            val = (maxid,sid,district,name,mobile,email,address)
            mycursor.execute(sql, val)
            mydb.commit()
        else:
            mycursor.execute("update cc_contact set district=%s,name=%s,mobile=%s,email=%s,address=%s where section_id=%s && name=%s",(district,name,mobile,email,address,sid,name))
            mydb.commit()
        msg="success"

    if act=="del":
        did=request.args.get("did")
        mycursor.execute("delete from cc_contact where id=%s",(did,))
        mydb.commit()
        return redirect(url_for('add_query1',sid=sid)) 

    return render_template('add_query1.html',msg=msg,sid=sid,act=act,data=data,data2=data2)


@app.route('/admin2', methods=['GET', 'POST'])
def admin2():
    msg=""
    mycursor = mydb.cursor()
    if request.method=='POST':
        input1=request.form['input']
        output=request.form['output']
        link=request.form['link']

        if link is None or link=="":
            url=""
        else:
            url=' <a href='+link+' target="_blank">Click Here</a>'

        output+=url
        
        mycursor.execute("SELECT max(id)+1 FROM cc_data")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1

        sql = "INSERT INTO cc_data(id,input,output) VALUES (%s,%s,%s)"
        val = (maxid,input1,output)
        mycursor.execute(sql, val)
        mydb.commit()

        
        print(mycursor.rowcount, "Added Success")
        
        return redirect(url_for('view_data',msg='success'))

    return render_template('admin2.html',msg=msg)

@app.route('/view_user', methods=['GET', 'POST'])
def view_user():
    value=[]
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM cc_register")
    data = mycursor.fetchall()

    
    return render_template('view_user.html', data=data)

@app.route('/page', methods=['GET', 'POST'])
def page():
    fn=request.args.get("fn")
   
    
    return render_template('page.html',fn=fn)



@app.route('/register',methods=['POST','GET'])
def register():
    msg=""
    act=""
    mycursor = mydb.cursor()
    name=""
    mobile=""
    mess=""
    uid=""
    if request.method=='POST':
        
        uname=request.form['uname']
        name=request.form['name']     
        mobile=request.form['mobile']
        email=request.form['email']
        location=request.form['location']
        pass1=request.form['pass']

        
        now = datetime.datetime.now()
        rdate=now.strftime("%d-%m-%Y")
        mycursor = mydb.cursor()

        mycursor.execute("SELECT count(*) FROM cc_register where uname=%s",(uname, ))
        cnt = mycursor.fetchone()[0]
        if cnt==0:
            mycursor.execute("SELECT max(id)+1 FROM cc_register")
            maxid = mycursor.fetchone()[0]
            if maxid is None:
                maxid=1
            
            uid=str(maxid)
            sql = "INSERT INTO cc_register(id, name, mobile, email, location,uname, pass,otp,status) VALUES (%s, %s, %s, %s, %s, %s, %s,%s,%s)"
            val = (maxid, name, mobile, email, location, uname, pass1,'','0')
            msg="success"
            mycursor.execute(sql, val)
            mydb.commit()            
            print(mycursor.rowcount, "record inserted.")
           
        else:
            msg="fail"
            
    return render_template('register.html',msg=msg,mobile=mobile,name=name,mess=mess,uid=uid)


def lg_translate(lg,output):
    result=""
    recognized_text=output
    try:
        available_languages = {
            'ta': 'Tamil',
            'hi': 'Hindi',
            'ml': 'Malayalam',
            'kn': 'Kannada',
            'te': 'Telugu',
            'mr': 'Marathi',
            'ur': 'Urdu',
            'bn': 'Bengali',
            'gu': 'Gujarati',
            'fr': 'French'
        }

        selected_languages=lg.split(',')
       
        for lang_code in selected_languages:
            lang_code = lang_code.strip()
            if lang_code in available_languages:
                translated = GoogleTranslator(source='en', target=lang_code).translate(recognized_text)
                print(f"Translation in {available_languages[lang_code]} ({lang_code}): {translated}")
                result=translated
            else:
                print(f"Language code {lang_code} not available.")

    except Exception as e:
        print("An error occurred during translation:", e)

    return result
    ###

####
def translate_text(text, source_language, target_language):
    api_key = 'AIzaSyDW9tvaQUsywmaILt73Go8Fy5mU6ILOixU'  # Replace with your API key
    url = f'https://translation.googleapis.com/language/translate/v2?key={api_key}'
    payload = {
        'q': text,
        'source': source_language,
        'target': target_language,
        'format': 'text'
    }
    response = requests.post(url, json=payload)
    translation_data = response.json()
    translated_text = translation_data
    #translation_data['data']['translations'][0]['translatedText']
    return translated_text

            
@app.route('/bot', methods=['GET', 'POST'])
def bot():
    msg=""
    output=""
    uname=""
    mm=""
    s=""
    xn=0
    val=""
    ##
    result=""
    
    ##
    if 'username' not in session:
        if request.method == 'POST':
            return "Session expired. Please log in again."
        return redirect(url_for('login_user'))

    uname = session['username']
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="110707",
        charset="utf8",
        database="lawyerbot"
    )

    cnt=0

    mycursor = mydb.cursor()

    mycursor.execute("SELECT * FROM cc_register where uname=%s",(uname, ))
    value = mycursor.fetchone()
    
    mycursor.execute("SELECT * FROM cc_data order by rand() limit 0,10")
    data=mycursor.fetchall()
            
    if request.method=='POST':
        msg_input=request.form['msg_input']
        lg=request.form['language']
        
        text=msg_input

        if not os.path.exists(DET_FILE):
            with open(DET_FILE, 'w') as _f: _f.write('1')
        ff=open(DET_FILE,"r")
        qry_st=ff.read().strip()
        ff.close()

        ## NLP helpers (kept for DB keyword search)
        stemmer = PorterStemmer()
        stopwords_set = TEXT_STOPWORDS

        def cleanTxt(text):
            text = text.lower()
            text = re.sub("#[A-Za-z0-9_]+", ' ', text)
            text = re.sub(r'@\S+|https?:\S+|http?:\S|[^A-Za-z0-9]+', ' ', text)
            text = " ".join([w for w in str(text).split() if w not in stopwords_set])
            text = " ".join([stemmer.stem(w) for w in text.split()])
            return text

        # --- Check if user is asking for lawyer recommendations ---
        lawyer_keywords = ['find lawyer', 'need lawyer', 'recommend lawyer', 'looking for lawyer', 
                           'lawyer near', 'best lawyer', 'show lawyer', 'lawyer in', 'advocate',
                           'attorney', 'legal help', 'legal advice', 'find advocate', 'contact lawyer']
        is_lawyer_query = any(kw in msg_input.lower() for kw in lawyer_keywords)

        if is_lawyer_query:
            # Extract district/city from query
            clean_msg = cleanTxt(msg_input)
            district_param = '%' + msg_input + '%'
            
            # Get APPROVED lawyers only from cc_lawyers with active accounts
            mycursor.execute("""
                SELECT l.* FROM cc_lawyers l 
                INNER JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id 
                WHERE (l.district LIKE %s OR l.city LIKE %s) AND la.status = 'active'
                LIMIT 5
            """, (district_param, district_param))
            lawyers = mycursor.fetchall()
            
            if len(lawyers) > 0:
                user_id = value[0] if value else None
                output = "<b>✅ Approved Lawyers Found:</b><br><br>"
                for lawyer in lawyers:
                    # lawyer: (id, name, specialization, experience, phone, email, address, district, city, rating, bio)
                    output += f"<div style='border:2px solid #10b981;padding:12px;margin-bottom:12px;border-radius:5px;background:#f0fdf4;'>"
                    output += f"<h5 style='color:#059669;'><i class='fas fa-check-circle'></i> {lawyer[1]}</h5>"
                    output += f"<b>Specialization:</b> {lawyer[2]}<br>"
                    output += f"<b>Experience:</b> {lawyer[3]} years<br>"
                    output += f"<b>Location:</b> {lawyer[8]}, {lawyer[7]}<br>"
                    output += f"<b>Rating:</b> ⭐ {lawyer[9]}/5<br>"
                    output += f"<b>Phone:</b> 📞 {lawyer[4]}<br>"
                    output += f"<form method='POST' action='/start_lawyer_chat/{lawyer[0]}' style='display:inline;margin-top:10px;'>"
                    output += f"<input type='hidden' name='case_description' value='Chat initiated from bot'>"
                    output += f"<button type='submit' style='background:#10b981;color:white;border:none;padding:8px 16px;border-radius:5px;cursor:pointer;font-weight:bold;'>"
                    output += f"💬 Chat with {lawyer[1].split()[0]}</button></form>"
                    output += f"</div><br>"
                
                ff = open(DET_FILE, "w")
                ff.write("1")
                ff.close()
                
                if lg == "":
                    val = output
                else:
                    val = lg_translate(lg, output)
                return val
            else:
                # No approved lawyers found
                output = "😕 No approved lawyers found in that area. Try asking with a different district name, or visit <a href='/lawyers' style='color:#10b981;'>Browse All Lawyers</a>"
                if lg == "":
                    val = output
                else:
                    val = lg_translate(lg, output)
                return val

        # --- District contact lookup (only when user explicitly asks) ---
        district_keywords = ['lawyer', 'contact', 'advocate', 'district', 'attorney']
        is_district_query = (qry_st=="2" and not any(kw in msg_input.lower() for kw in ['section', 'ipc', 'punishment', 'offense', 'crime', 'what is', 'explain', 'tell me'])) or any(kw in msg_input.lower() for kw in district_keywords)

        if is_district_query:
            clean_msg=cleanTxt(msg_input)
            cleaned='%'+clean_msg+'%'
            mm='%'+clean_msg+'%'
            
            mycursor.execute("SELECT count(*) FROM cc_contact where district like %s",(cleaned,))
            cnt1=mycursor.fetchone()[0]
            if cnt1==0:
                mm='%'+msg_input+'%'
            
            mycursor.execute("SELECT count(*) FROM cc_contact where district like %s",(mm,))
            cnt=mycursor.fetchone()[0]

            if cnt>0:
                dd3="<b>Lawyer Contacts:</b>"
                mycursor.execute("SELECT * FROM cc_contact where district like %s",(mm,))
                dd=mycursor.fetchall()
                for dd1 in dd:
                    dd3+="<br><br>\U0001f464 <b>"+dd1[3]+"</b>"
                    dd3+="<br>\U0001f4cd "+dd1[6]+", "+dd1[2]
                    dd3+="<br>\U0001f4de "+str(dd1[4])+" &bull; \u2709\ufe0f "+dd1[5]
                output=dd3
                ff=open(DET_FILE,"w")
                ff.write("1")
                ff.close()
                if lg=="":
                    val=output
                else:
                    val=lg_translate(lg,output)
                return val
            # If no contacts found for that district, fall through to AI query
            # instead of showing 'no lawyers found'

        # --- Main legal query – powered by Groq LLM ---
        if True:
            # Step 1: search DB for relevant IPC sections
            clean_msg=cleanTxt(msg_input)
            like_clean='%'+clean_msg+'%'
            like_raw='%'+msg_input+'%'

            mycursor.execute("SELECT count(*) FROM cc_data where user_query like %s or offense like %s or description like %s",(like_clean,like_clean,like_clean))
            cnt1=mycursor.fetchone()[0]
            mm = like_clean if cnt1>0 else like_raw

            mycursor.execute("SELECT * FROM cc_data where user_query like %s or offense like %s or description like %s limit 0,5",(mm,mm,mm))
            dd=mycursor.fetchall()

            # Step 2: build context string from DB results
            db_context=""
            for dd1 in dd:
                db_context += f"\nIPC Section: {dd1[4]}\n"
                db_context += f"Description: {dd1[1]}\n"
                if dd1[2]:
                    db_context += f"Offense: {dd1[2]}\n"
                if dd1[3]:
                    db_context += f"Punishment: {dd1[3]}\n"

            # Step 3: call Groq LLM
            ai_response = ask_groq(msg_input, db_context)

            # Step 4: format the response with IPC details + AI explanation
            output = ""
            if dd:
                for dd1 in dd:
                    output += "<br><h5>IPC Section: "+str(dd1[4])+"</h5>"
                    output += "<br>Description:<br>"+str(dd1[1])
                    if dd1[2]:
                        output += "<br><br>Offense:<br>"+str(dd1[2])
                    if dd1[3]:
                        output += "<br><br>Punishment:<br>"+str(dd1[3])+"<br>"

            # Add AI explanation
            output += "<br><br><b>AI Explanation:</b><br>" + ai_response.replace('\n', '<br>')

            # Mention lawyer contacts available (but don't force state change)
            mycursor.execute("SELECT count(*) FROM cc_contact")
            cnt4=mycursor.fetchone()[0]
            if cnt4>0:
                output+="<br><br><small style='color:#888'>\U0001f4a1 Need a lawyer? Just type a district name (e.g. \"Chennai\") to find contacts.</small>"
            ff=open(DET_FILE,"w")
            ff.write("1")
            ff.close()

            if lg=="":
                val=output
            else:
                val=lg_translate(lg,output)
            return val


    return render_template('bot.html',msg=msg,output=output,uname=uname,data=data,value=value)   


#BERT-Feature Extraction
def BERT():
    super(BERTLM, self).__init__()
    self.vocab = vocab
    self.embed_dim =embed_dim
    self.tok_embed = Embedding(self.vocab.size, embed_dim, self.vocab.padding_idx)
    self.pos_embed = LearnedPositionalEmbedding(embed_dim, device=local_rank)
    self.seg_embed = Embedding(2, embed_dim, None)

    self.out_proj_bias = nn.Parameter(torch.Tensor(self.vocab.size))

    self.layers = nn.ModuleList()
    for i in range(layers):
        self.layers.append(TransformerLayer(embed_dim, ff_embed_dim, num_heads, dropout))
    self.emb_layer_norm = LayerNorm(embed_dim)
    self.one_more = nn.Linear(embed_dim, embed_dim)
    self.one_more_layer_norm = LayerNorm(embed_dim)
    self.one_more_nxt_snt = nn.Linear(embed_dim, embed_dim) 
    self.nxt_snt_pred = nn.Linear(embed_dim, 1)
    self.dropout = dropout
    self.device = local_rank

    if approx == "none":
        self.approx = None
    elif approx == "adaptive":
        self.approx = nn.AdaptiveLogSoftmaxWithLoss(self.embed_dim, self.vocab.size, [10000, 20000, 200000])
    else:
        raise NotImplementedError("%s has not been implemented"%approx)
    self.reset_parameters()

def reset_parameters(self):
    nn.init.constant_(self.out_proj_bias, 0.)
    nn.init.constant_(self.nxt_snt_pred.bias, 0.)
    nn.init.constant_(self.one_more.bias, 0.)
    nn.init.constant_(self.one_more_nxt_snt.bias, 0.)
    nn.init.normal_(self.nxt_snt_pred.weight, std=0.02)
    nn.init.normal_(self.one_more.weight, std=0.02)
    nn.init.normal_(self.one_more_nxt_snt.weight, std=0.02)

def work(self, inp, seg=None, layers=None):
   
    if layers is not None:
        tot_layers = len(self.layers)
        for x in layers:
            if not (-tot_layers <= x < tot_layers):
                raise ValueError('layer %d out of range '%x)
        layers = [ (x+tot_layers if x <0 else x) for x in layers]
        max_layer_id = max(layers)
    
    seq_len, bsz = inp.size()
    if seg is None:
        seg = torch.zeros_like(inp)
    x = self.tok_embed(inp) + self.seg_embed(seg) + self.pos_embed(inp)
    x = self.emb_layer_norm(x)
    x = F.dropout(x, p=self.dropout, training=self.training)
    padding_mask = torch.eq(inp, self.vocab.padding_idx)
    if not padding_mask.any():
        padding_mask = None
    
    xs = []
    for layer_id, layer in enumerate(self.layers):
        x, _ ,_ = layer(x, self_padding_mask=padding_mask)
        xs.append(x)
        if layers is not None and layer_id >= max_layer_id:
            break
    
    if layers is not None:
        x = torch.stack([xs[i] for i in layers])
        z = torch.tanh(self.one_more_nxt_snt(x[:,0,:,:]))
    else:
        z = torch.tanh(self.one_more_nxt_snt(x[0]))
    return x, z

def forward(self, truth, inp, seg, msk, nxt_snt_flag):
    seq_len, bsz = inp.size()
    x = self.tok_embed(inp) + self.seg_embed(seg) + self.pos_embed(inp)
    x = self.emb_layer_norm(x)
    x = F.dropout(x, p=self.dropout, training=self.training)
    padding_mask = torch.eq(truth, self.vocab.padding_idx)
    if not padding_mask.any():
        padding_mask = None
    for layer in self.layers:
        x, _ ,_ = layer(x, self_padding_mask=padding_mask)

    masked_x = x.masked_select(msk.unsqueeze(-1))
    masked_x = masked_x.view(-1, self.embed_dim)
    gold = truth.masked_select(msk)
    
    y = self.one_more_layer_norm(gelu(self.one_more(masked_x)))
    out_proj_weight = self.tok_embed.weight

    if self.approx is None:
        log_probs = torch.log_softmax(F.linear(y, out_proj_weight, self.out_proj_bias), -1)
    else:
        log_probs = self.approx.log_prob(y)

    loss = F.nll_loss(log_probs, gold, reduction='mean')

    z = torch.tanh(self.one_more_nxt_snt(x[0]))
    nxt_snt_pred = torch.sigmoid(self.nxt_snt_pred(z).squeeze(1))
    nxt_snt_acc = torch.eq(torch.gt(nxt_snt_pred, 0.5), nxt_snt_flag).float().sum().item()
    nxt_snt_loss = F.binary_cross_entropy(nxt_snt_pred, nxt_snt_flag.float(), reduction='mean')
    
    tot_loss = loss + nxt_snt_loss
    
    _, pred = log_probs.max(-1)
    tot_tokens = msk.float().sum().item()
    acc = torch.eq(pred, gold).float().sum().item()
    
    return (pred, gold), tot_loss, acc, tot_tokens, nxt_snt_acc, bsz
####
#LSTM-Classification
class LSTM():
    INPUT_VECTOR_LENGTH = 20
    OUTPUT_VECTORLENGTH = 20
    minimum_length = 2
    maximum_length = 20
    sample_size = 30000 
    WORD_START = 1
    WORD_PADDING = 0

    def extract_converstionIDs(conversation_lines):
        conversations = []
        for line in conversation_lines[:-1]:
            split_line = line.split(' +++$+++ ')[-1][1:-1].replace("'","").replace(" ","")
            conversations.append(split_line.split(','))
        return conversations

    def extract_quesans_pairs(linetoID_mapping,conversations):
        questions = []
        answers = []
        for con in conversations:
            for i in range(len(con)-1):
                questions.append(linetoID_mapping[con[i]])
                answers.append(linetoID_mapping[con[i+1]])
        return questions,answers
    def transform_text(input_text):
        input_text = input_text.lower()
        input_text = re.sub(r"I'm", "I am", input_text)
        input_text = re.sub(r"he's", "he is", input_text)
        input_text = re.sub(r"she's", "she is", input_text)
        input_text = re.sub(r"it's", "it is", input_text)
        input_text = re.sub(r"that's", "that is", input_text)
        input_text = re.sub(r"what's", "that is", input_text)
        input_text = re.sub(r"where's", "where is", input_text)
        input_text = re.sub(r"how's", "how is", input_text)
        input_text = re.sub(r"\'ll", " will", input_text)
        input_text = re.sub(r"\'ve", " have", input_text)
        input_text = re.sub(r"\'re", " are", input_text)
        input_text = re.sub(r"\'d", " would", input_text)
        input_text = re.sub(r"\'re", " are", input_text)
        input_text = re.sub(r"won't", "will not", input_text)
        input_text = re.sub(r"can't", "cannot", input_text)
        input_text = re.sub(r"n't", " not", input_text)
        input_text = re.sub(r"'til", "until", input_text)
        input_text = re.sub(r"[-()\"#/@;:<>{}`+=~|]", "", input_text)
        input_text = " ".join(input_text.split())
        return input_text

    def filter_ques_ans(clean_questions,clean_answers):
        # Filter out the questions that are too short/long
        short_questions_temp = []
        short_answers_temp = []
        for i, question in enumerate(clean_questions):
            if len(question.split()) >= minimum_length and len(question.split()) <= maximum_length:
                short_questions_temp.append(question)
                short_answers_temp.append(clean_answers[i])
        short_questions = []
        short_answers = []
        for i, answer in enumerate(short_answers_temp):
            if len(answer.split()) >= minimum_length and len(answer.split()) <= maximum_length:
                short_answers.append(answer)
                short_questions.append(short_questions_temp[i])
        return short_questions,short_answers

    def create_vocabulary(tokenized_ques,tokenized_ans):
        vocabulary = {}
        for question in tokenized_ques:
            for word in question:
                if word not in vocabulary:
                    vocabulary[word] = 1
                else:
                    vocabulary[word] += 1
        for answer in tokenized_ans:
            for word in answer:
                if word not in vocabulary:
                    vocabulary[word] = 1
                else:
                    vocabulary[word] += 1  
        return vocabulary

    def create_encoding_decoding(vocabulary):
        threshold = 15
        count = 0
        for k,v in vocabulary.items():
            if v >= threshold:
                count += 1
        vocab_size  = 2 
        encoding = {}
        decoding = {1: 'START'}
        for word, count in vocabulary.items():
            if count >= threshold:
                encoding[word] = vocab_size 
                decoding[vocab_size ] = word
                vocab_size += 1
        return encoding,decoding,vocab_size
    def transform(encoding, data, vector_size=20):
        transformed_data = np.zeros(shape=(len(data), vector_size))
        for i in range(len(data)):
            for j in range(min(len(data[i]), vector_size)):
                try:
                    transformed_data[i][j] = encoding[data[i][j]]
                except:
                    transformed_data[i][j] = encoding['<UNKNOWN>']
        return transformed_data
    def create_gloveEmbeddings(encoding,size):
        file = open(GLOVE_MODEL, mode='rt', encoding='utf8')
        words = set()
        word_to_vec_map = {}
        for line in file:
            line = line.strip().split()
            word = line[0]
            words.add(word)
            word_to_vec_map[word] = np.array(line[1:], dtype=np.float64)
        embedding_matrix = np.zeros((size, 50))
        for word,index in encoding.items():
            try:
                embedding_matrix[index, :] = word_to_vec_map[word.lower()]
            except: continue
        return embedding_matrix

    def create_model(dict_size,embed_layer,hidden_dim):
    
        encoder_inputs = Input(shape=(maximum_length, ), dtype='int32',)
        encoder_embedding = embed_layer(encoder_inputs)
        encoder_LSTM = LSTM(hidden_dim, return_state=True)
        encoder_outputs, state_h, state_c = encoder_LSTM(encoder_embedding)
        decoder_inputs = Input(shape=(maximum_length, ), dtype='int32',)
        decoder_embedding = embed_layer(decoder_inputs)
        decoder_LSTM = LSTM(hidden_dim, return_state=True, return_sequences=True)
        decoder_outputs, _, _ = decoder_LSTM(decoder_embedding, initial_state=[state_h, state_c])
        outputs = TimeDistributed(Dense(dict_size, activation='softmax'))(decoder_outputs)
        model = Model([encoder_inputs, decoder_inputs], outputs)
        return model

    def prediction_answer(user_input,model):
        transformed_input = transform_text(user_input)
        input_tokens = [nltk.word_tokenize(transformed_input)]
        input_tokens = [input_tokens[0][::-1]]  #reverseing input seq
        encoder_input = transform(encoding, input_tokens, 20)
        decoder_input = np.zeros(shape=(len(encoder_input), OUTPUT_VECTORLENGTH))
        decoder_input[:,0] = WORD_START
        for i in range(1, OUTPUT_VECTORLENGTH):
            pred_output = model.predict([encoder_input, decoder_input]).argmax(axis=2)
            decoder_input[:,i] = pred_output[:,i]
        return pred_output

##########################
@app.route('/sign')
def sign():
    return render_template('sign.html')

@app.route('/signUpUser', methods=['POST'])
def signUpUser():
    user =  request.form['username'];
    password = request.form['password'];

    print(password)
    return json.dumps({'status':'OK','user':user,'pass':password});


@app.route('/view_data', methods=['GET', 'POST'])
def view_data():
    data=[]
    msg=request.args.get("msg")
    act=request.args.get("act")
    url=""
    mycursor = mydb.cursor()

    mycursor.execute("SELECT * FROM cc_data")
    data1 = mycursor.fetchall()

    for dat in data1:
        dt=[]
        txt=dat[1]
        t=txt.replace("\t\r\n","<br>")
        #if "\t\r\n" in dat[2]:

        dt.append(dat[0])
        dt.append(t)
        dt.append(dat[2])
        dt.append(dat[3])
        dt.append(dat[4])
        
        data.append(dt)
            
            
    

    
    
    
    return render_template('view_data.html',msg=msg,act=act,data=data)

@app.route('/down', methods=['GET', 'POST'])
def down():
    fn = request.args.get('fname')
    path=os.path.join(UPLOAD_FOLDER, fn)
    return send_file(path, as_attachment=True)

@app.route('/logout')
def logout():
    # remove the username from the session if it is there
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/lawyers', methods=['GET', 'POST'])
def lawyers():
    """Display lawyers and filter by district - show only actively logged-in lawyers"""
    msg = ""
    mycursor = mydb.cursor()
    district_filter = request.args.get('district', '')
    
    # Query only lawyers who are approved and have logged in within last 24 hours
    if district_filter:
        mycursor.execute("""
            SELECT l.*, 
                   CASE WHEN la.last_login IS NOT NULL 
                        AND la.last_login > DATE_SUB(NOW(), INTERVAL 24 HOUR) 
                        THEN 1 ELSE 0 END as is_online
            FROM cc_lawyers l
            INNER JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id
            WHERE l.district LIKE %s 
            AND la.status = 'active'
            AND la.last_login IS NOT NULL
            ORDER BY la.last_login DESC
        """, (f'%{district_filter}%',))
    else:
        mycursor.execute("""
            SELECT l.*, 
                   CASE WHEN la.last_login IS NOT NULL 
                        AND la.last_login > DATE_SUB(NOW(), INTERVAL 24 HOUR) 
                        THEN 1 ELSE 0 END as is_online
            FROM cc_lawyers l
            INNER JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id
            WHERE la.status = 'active'
            AND la.last_login IS NOT NULL
            ORDER BY la.last_login DESC
        """)
    
    lawyers_list = mycursor.fetchall()
    
    # Get distinct districts for filter
    mycursor.execute("""
        SELECT DISTINCT l.district
        FROM cc_lawyers l
        INNER JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id
        WHERE la.status = 'active'
        AND la.last_login IS NOT NULL
    """)
    districts = [row[0] for row in mycursor.fetchall()]
    
    return render_template('lawyers.html', lawyers=lawyers_list, districts=districts, selected_district=district_filter)

@app.route('/lawyer/<int:lawyer_id>', methods=['GET', 'POST'])
def lawyer_profile(lawyer_id):
    """Display individual lawyer profile"""
    if 'username' not in session:
        return redirect(url_for('login_user'))
    
    msg = ""
    user_id = None
    mycursor = mydb.cursor()
    
    # Get user ID
    uname = session['username']
    mycursor.execute("SELECT id FROM cc_register WHERE uname=%s", (uname,))
    user_result = mycursor.fetchone()
    if user_result:
        user_id = user_result[0]
    
    # Get lawyer details
    mycursor.execute("SELECT * FROM cc_lawyers WHERE id=%s", (lawyer_id,))
    lawyer = mycursor.fetchone()
    
    if request.method == 'POST':
        case_description = request.form.get('case_description', '')
        
        mycursor.execute(
            "INSERT INTO cc_requests (user_id, lawyer_id, case_description) VALUES (%s, %s, %s)",
            (user_id, lawyer_id, case_description)
        )
        mydb.commit()
        msg = "Request sent successfully! Lawyer will respond soon."
    
    return render_template('lawyer_profile.html', lawyer=lawyer, msg=msg)

@app.route('/requests', methods=['GET'])
def user_requests():
    """View all user requests"""
    if 'username' not in session:
        return redirect(url_for('login_user'))
    
    mycursor = mydb.cursor()
    uname = session['username']
    
    # Get user ID
    mycursor.execute("SELECT id FROM cc_register WHERE uname=%s", (uname,))
    user_result = mycursor.fetchone()
    user_id = user_result[0] if user_result else None
    
    # Get all requests for this user
    mycursor.execute("""
        SELECT r.id, r.lawyer_id, r.case_description, r.status, r.created_at, l.name, l.phone, l.email
        FROM cc_requests r
        JOIN cc_lawyers l ON r.lawyer_id = l.id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC
    """, (user_id,))
    requests_list = mycursor.fetchall()
    
    return render_template('user_requests.html', requests=requests_list)

@app.route('/admin_lawyers', methods=['GET', 'POST'])
def admin_lawyers():
    """Admin page to manage lawyers - view pending and approved"""
    # Check if user is logged in as admin
    is_admin = 'username' in session
    
    msg = ""
    status_filter = request.args.get('status', 'all')  # all, pending, approved
    mycursor = mydb.cursor()
    
    if status_filter == 'pending':
        mycursor.execute("""
            SELECT l.*, la.status as account_status 
            FROM cc_lawyers l 
            LEFT JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id 
            WHERE la.status = 'pending' OR la.status IS NULL
        """)
    elif status_filter == 'approved':
        mycursor.execute("""
            SELECT l.*, la.status as account_status 
            FROM cc_lawyers l 
            LEFT JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id 
            WHERE la.status = 'active'
        """)
    else:
        mycursor.execute("""
            SELECT l.*, la.status as account_status 
            FROM cc_lawyers l 
            LEFT JOIN cc_lawyer_accounts la ON l.id = la.lawyer_id
        """)
    
    lawyers_list = mycursor.fetchall()
    
    return render_template('admin_lawyers.html', lawyers=lawyers_list, msg=msg, status_filter=status_filter, is_admin=is_admin)

@app.route('/admin_approve_lawyer/<int:lawyer_id>', methods=['GET'])
def admin_approve_lawyer(lawyer_id):
    """Approve a pending lawyer"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    mycursor = mydb.cursor()
    mycursor.execute(
        "UPDATE cc_lawyer_accounts SET status='active' WHERE lawyer_id=%s",
        (lawyer_id,)
    )
    mydb.commit()
    
    return redirect(url_for('admin_lawyers', status='pending'))

@app.route('/admin_reject_lawyer/<int:lawyer_id>', methods=['GET'])
def admin_reject_lawyer(lawyer_id):
    """Reject a pending lawyer"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    mycursor = mydb.cursor()
    mycursor.execute("DELETE FROM cc_lawyer_accounts WHERE lawyer_id=%s", (lawyer_id,))
    mycursor.execute("DELETE FROM cc_lawyers WHERE id=%s", (lawyer_id,))
    mydb.commit()
    
    return redirect(url_for('admin_lawyers', status='pending'))

@app.route('/admin_add_lawyer', methods=['POST'])
def admin_add_lawyer():
    """Add new lawyer"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name', '')
    phone = request.form.get('phone', '')
    email = request.form.get('email', '')
    specialization = request.form.get('specialization', '')
    experience = request.form.get('experience', 0)
    city = request.form.get('city', '')
    district = request.form.get('district', '')
    address = request.form.get('address', '')
    rating = request.form.get('rating', 4.0)
    bio = request.form.get('bio', '')
    
    mycursor = mydb.cursor()
    mycursor.execute("""
        INSERT INTO cc_lawyers (name, specialization, experience, phone, email, address, district, city, rating, bio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, specialization, experience, phone, email, address, district, city, rating, bio))
    mydb.commit()
    
    return redirect(url_for('admin_lawyers'))

@app.route('/admin_delete_lawyer/<int:lawyer_id>', methods=['GET'])
def admin_delete_lawyer(lawyer_id):
    """Delete lawyer"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    mycursor = mydb.cursor()
    mycursor.execute("DELETE FROM cc_lawyer_accounts WHERE lawyer_id=%s", (lawyer_id,))
    mycursor.execute("DELETE FROM cc_lawyers WHERE id=%s", (lawyer_id,))
    mydb.commit()
    
    return redirect(url_for('admin_lawyers'))


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    if 'username' not in session:
        return redirect(url_for('login_user'))
    
    msg = ""
    mycursor = mydb.cursor()
    uname = session['username']
    
    mycursor.execute("SELECT * FROM cc_register WHERE uname=%s", (uname,))
    user = mycursor.fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        mobile = request.form.get('mobile', '')
        email = request.form.get('email', '')
        location = request.form.get('location', '')
        
        mycursor.execute("""
            UPDATE cc_register SET name=%s, mobile=%s, email=%s, location=%s WHERE uname=%s
        """, (name, mobile, email, location, uname))
        mydb.commit()
        msg = "Profile updated successfully!"
    
    return render_template('edit_profile.html', user=user, msg=msg)

@app.route('/edit_lawyer_profile', methods=['GET', 'POST'])
def edit_lawyer_profile():
    """Edit lawyer profile"""
    if 'lawyer_id' not in session:
        return redirect(url_for('login_lawyer'))
    
    msg = ""
    mycursor = mydb.cursor()
    lawyer_id = session['lawyer_id']
    
    mycursor.execute("SELECT * FROM cc_lawyers WHERE id=%s", (lawyer_id,))
    lawyer = mycursor.fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        specialization = request.form.get('specialization', '')
        experience = request.form.get('experience', 0)
        city = request.form.get('city', '')
        district = request.form.get('district', '')
        address = request.form.get('address', '')
        bio = request.form.get('bio', '')
        
        mycursor.execute("""
            UPDATE cc_lawyers SET name=%s, phone=%s, email=%s, specialization=%s, 
            experience=%s, city=%s, district=%s, address=%s, bio=%s WHERE id=%s
        """, (name, phone, email, specialization, experience, city, district, address, bio, lawyer_id))
        mydb.commit()
        msg = "Profile updated successfully!"
        
        # Update session with new name
        session['lawyer_name'] = name
    
    return render_template('edit_lawyer_profile.html', lawyer=lawyer, msg=msg)

@app.route('/start_lawyer_chat/<int:lawyer_id>', methods=['POST'])
def start_lawyer_chat(lawyer_id):
    """Start chat with a specific lawyer from bot"""
    if 'username' not in session:
        return redirect(url_for('login_user'))
    
    mycursor = mydb.cursor()
    uname = session['username']
    
    # Get user ID
    mycursor.execute("SELECT id FROM cc_register WHERE uname=%s", (uname,))
    user_result = mycursor.fetchone()
    user_id = user_result[0] if user_result else None
    
    # Check if already has a request with this lawyer
    mycursor.execute(
        "SELECT id FROM cc_requests WHERE user_id=%s AND lawyer_id=%s",
        (user_id, lawyer_id)
    )
    existing = mycursor.fetchone()
    
    if existing:
        request_id = existing[0]
    else:
        # Create new request
        case_description = request.form.get('case_description', 'Direct chat from bot')
        mycursor.execute(
            "INSERT INTO cc_requests (user_id, lawyer_id, case_description) VALUES (%s, %s, %s)",
            (user_id, lawyer_id, case_description)
        )
        mydb.commit()
        request_id = mycursor.lastrowid
    
    return redirect(url_for('chat', request_id=request_id))

@app.route('/register_lawyer', methods=['GET', 'POST'])
def register_lawyer():
    """Register a new lawyer"""
    msg = ""
    mycursor = mydb.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        specialization = request.form.get('specialization', '')
        experience = request.form.get('experience', 0)
        city = request.form.get('city', '')
        district = request.form.get('district', '')
        address = request.form.get('address', '')
        bio = request.form.get('bio', '')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Check if username already exists
        mycursor.execute("SELECT COUNT(*) FROM cc_lawyer_accounts WHERE username=%s", (username,))
        if mycursor.fetchone()[0] > 0:
            msg = "fail"
            return render_template('register_lawyer.html', msg=msg)
        
        # Insert lawyer profile
        mycursor.execute("""
            INSERT INTO cc_lawyers (name, phone, email, specialization, experience, city, district, address, bio, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, email, specialization, experience, city, district, address, bio, 4.5))
        mydb.commit()
        lawyer_id = mycursor.lastrowid
        
        # Create lawyer account with pending status
        mycursor.execute("""
            INSERT INTO cc_lawyer_accounts (lawyer_id, username, password, status, last_login)
            VALUES (%s, %s, %s, %s, NULL)
        """, (lawyer_id, username, password, 'pending'))
        mydb.commit()
        
        msg = "success"
    
    return render_template('register_lawyer.html', msg=msg)

@app.route('/login_lawyer', methods=['GET', 'POST'])
def login_lawyer():
    """Login for lawyers"""
    msg = ""
    mycursor = mydb.cursor()
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Check credentials and status
        mycursor.execute("""
            SELECT la.lawyer_id, l.name, la.status, la.id
            FROM cc_lawyer_accounts la
            JOIN cc_lawyers l ON la.lawyer_id = l.id
            WHERE la.username=%s AND la.password=%s
        """, (username, password))
        
        result = mycursor.fetchone()
        
        if result:
            lawyer_id, lawyer_name, status, account_id = result
            
            if status == 'pending':
                msg = "Your account is pending admin approval. Please wait."
            elif status == 'inactive':
                msg = "Your account has been deactivated."
            else:
                # Update last_login timestamp
                mycursor.execute(
                    "UPDATE cc_lawyer_accounts SET last_login=NOW() WHERE id=%s",
                    (account_id,)
                )
                mydb.commit()
                
                # Set session and redirect
                session['lawyer_id'] = lawyer_id
                session['lawyer_name'] = lawyer_name
                return redirect(url_for('lawyer_dashboard'))
        else:
            msg = "Invalid credentials!"
    
    return render_template('login_lawyer.html', msg=msg)

@app.route('/lawyer_dashboard')
def lawyer_dashboard():
    """Lawyer dashboard"""
    if 'lawyer_id' not in session:
        return redirect(url_for('login_lawyer'))
    
    mycursor = mydb.cursor()
    lawyer_id = session['lawyer_id']
    
    # Get lawyer details
    mycursor.execute("SELECT * FROM cc_lawyers WHERE id=%s", (lawyer_id,))
    lawyer = mycursor.fetchone()
    
    # Get requests for this lawyer
    mycursor.execute("""
        SELECT r.id, r.user_id, u.name as user_name, u.email, r.case_description, r.created_at
        FROM cc_requests r
        JOIN cc_register u ON r.user_id = u.id
        WHERE r.lawyer_id=%s
        ORDER BY r.created_at DESC
    """, (lawyer_id,))
    requests = mycursor.fetchall()
    
    return render_template('lawyer_dashboard.html', lawyer=lawyer, requests=requests)

@app.route('/chat/<int:request_id>', methods=['GET', 'POST'])
def chat(request_id):
    """Chat between user and lawyer on a request"""
    if 'username' not in session:
        return redirect(url_for('login_user'))
    
    mycursor = mydb.cursor()
    uname = session['username']
    
    # Get user ID
    mycursor.execute("SELECT id FROM cc_register WHERE uname=%s", (uname,))
    user_result = mycursor.fetchone()
    user_id = user_result[0] if user_result else None
    
    # Get request details
    mycursor.execute("""
        SELECT r.*, l.name as lawyer_name, l.phone, l.email, u.name as user_name
        FROM cc_requests r
        JOIN cc_lawyers l ON r.lawyer_id = l.id
        JOIN cc_register u ON r.user_id = u.id
        WHERE r.id = %s
    """, (request_id,))
    request_details = mycursor.fetchone()
    
    if request.method == 'POST':
        message_text = request.form.get('message', '')
        sender_type = request.form.get('sender_type', 'user')
        
        mycursor.execute(
            "INSERT INTO cc_messages (request_id, sender_id, sender_type, message) VALUES (%s, %s, %s, %s)",
            (request_id, user_id, sender_type, message_text)
        )
        mydb.commit()
    
    # Get all messages for this request
    mycursor.execute("""
        SELECT sender_id, sender_type, message, created_at
        FROM cc_messages
        WHERE request_id = %s
        ORDER BY created_at ASC
    """, (request_id,))
    messages = mycursor.fetchall()
    
    return render_template('chat.html', request_details=request_details, messages=messages, user_id=user_id)


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0', port=5000)
