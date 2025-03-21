import sqlite3
from flask import Flask, render_template, request, redirect, flash, jsonify, url_for, session
from flask import send_from_directory, abort
import pyotp
import os
import requests
from config import Config
from flask_talisman import Talisman
import uuid
import sqlite3
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = '468eac327af780aebd4d613d9a619cd8f9e94a2b964240a2b7d5cafedce77853'  # Secret key required for Flask sessions, provides randomenss 

# Security Headers using Flask-Talisman, to enforce security measure like if data is comming from the same and valid origin 
csp = {
    'default-src': [
        '\'self\'',
        'https://fonts.googleapis.com',
        'https://fonts.gstatic.com'
    ],
    'style-src': [
        '\'self\'',
        'https://fonts.googleapis.com'
    ],
    'font-src': [
        '\'self\'',
        'https://fonts.gstatic.com'
    ],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\''
    ],
    'connect-src': [
        '\'self\''
    ]
}

Talisman(app, content_security_policy=csp, force_https=False)

# use to store Scan Results in Memory (
scan_results = {}

# Signature Database which contains the signatureso known viruses 
virus_signatures = {
    'EICAR_Test': b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*',
    'Trojan_Generic': b'\x4D\x5A\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xFF\xFF\x00\x00',
    'Worm_Malicious': b'\x50\x4B\x03\x04\x14\x00\x06\x00',
    'Virus_Script': b'eval('
}

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row  # Enables accessing columns by name
    return conn

@app.before_request
def refresh_session_timeout():
    session.permanent = True  # This enables session expiry based on Config.PermanentSessionLifetime

def virus_scan(file_path):
    with open(file_path, 'rb') as file:# opens the file 
        content = file.read()#reads the file 
        for virus_name, signature in virus_signatures.items(): # for Loop to loop through each virus signature in the dictionary
            if signature in content:# check if the current signature is in the dictionary 
                return f"Threat Detected: {virus_name}"# if found then print thread detected 
    return "No Threats Found"# if not then print no threats found 

#  Heuristic Scan Function to check known suspicious patterns
def heuristic_check(filepath):
    with open(filepath, 'r', errors='ignore') as file: #it opens file in read mode  
        content = file.read() # Stores the file content in the string 
        suspicious_words = ['eval(', 'base64_decode', 'exec(', 'powershell', 'cmd.exe', 'shell_exec'] #List of suspicious keywords often used in malware or malicious scripts
        for keyword in suspicious_words:#Check if any suspicious keyword appears in the file content
            if keyword in content:
                return "Threat Detected: Suspicious Script" # prints the threat detected if a keyword is found
        if 'function ' in content and 'eval(' in content:# look for obfuscated functions 
            return "Threat Detected: Obfuscated Function"
        if filepath.endswith('.bat') or filepath.endswith('.exe'):# check if the file file extension is executable or batch
            return "Threat Detected: Potential Executable"
    return "No Threats Found"

# File Scan Function to scan for known suspiscious patterms and known viruses 
def file_scan(file_path):
    scan_result = virus_scan(file_path)  # Runs the signature scan to scan for known viruses or malware 
    
    # If Signature Scan is Clean and no virus found , then run Heuristic Analysis
    if scan_result == "No Threats Found":
        scan_result = heuristic_check(file_path)#Runs the heurisitc analysis 
    
    
    file_name = os.path.basename(file_path)# Get the file name
    
    
    scan_results[file_name] = scan_result# Store the Scan Result
    
    return scan_result

# Route to handle user login
# @app.route('/login', methods=['GET', 'POST'])  
# def login():
#     if request.method == 'POST':# checks if the user method is POST
#         username = request.form.get('username')# gets the username from the form and store it 
#         password = request.form.get('password')#gets the password from the form and store it


#         if username == 'test1' and password == 'testpass1':# checks if the user name and password match the dummy name and password
#             session['authenticated'] = True # if they are same then set user as authenticated in session
#             session.modified = True  # ensures session is updated

#             # print("Session Data After Login:", session)  # Debugging

#             return jsonify({'success': True, 'redirect_url': url_for('index')}) # sends the sucess response 
#         else:
#             return jsonify({'success': False, 'error': 'Invalid credentials'}), 401 # sends the error response if login fails 

#     # If GET request, render login page
#     return render_template('login.html') 


@app.route('/login', methods=['GET', 'POST'])  
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['authenticated'] = True
            session['username'] = username
            session.permanent = True  # Set session as permanent to apply timeout
            session['was_logged_in'] = True  # ✅ Add this flag
            return jsonify({'success': True, 'redirect_url': url_for('index')})
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clears everything including 'was_logged_in'
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/')
def index():
    print(session)  # Check what's in the session on each request
    if 'authenticated' not in session:
      if session.get('was_logged_in'):
        flash('Session expired! Please log in again.')
      return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # print("Session Data Before Upload:", session)  # Debugging

    if not session.get('authenticated'):#  checks if the user is authenticated before allowing file upload
         return jsonify({'error': 'Session expired!.Please log in again.'}), 401 # Return 401 if not logged in

    if 'file' not in request.files:  #  checks if a file was uploaded in the request
        return jsonify({'error': 'No file part'}), 400  #Return 400 if no file was uploaded

    get_file = request.files['file'] # Get and stores the uplaoded file
    if get_file.filename == '':# checks if the user selected a file 
        return jsonify({'error': 'No selected file'}), 400# Return 400 if now file wa selected

    if get_file and allowed_file(get_file.filename):# checks if the file is allowed 
        filename = str(uuid.uuid4()) + os.path.splitext(get_file.filename)[1]# generates the unique file name to avoid overwriting the existing files 
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)#creates the full path to save file 
        get_file.save(filepath)

        result = file_scan(filepath)# check file for tjreats
        return jsonify({ # Retunrs the JSON response with scan results 
            'filename': filename,
            'result': result
        })
    else:
        return jsonify({'error': 'Invalid file type'}), 400 # Return 400 if the file tpye is not allowed 


# Route to file download 
@app.route('/download/<filename>')
def download_file(filename):
    if not session.get('authenticated'):# checks if the user is authenticated beofre allowing file download 
        return redirect(url_for('login'))#if not then redirect to login 

    # Check if the file exists
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash("File not found.")# shows erro if file dont exist 
        return redirect(url_for('index'))# Redirects to the main page


  
    if filename in scan_results:  # Check the scan result before allowing download
        if scan_results[filename] == "No Threats Found":
           
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)# checks if the file user wants to download is in upload folder 
        else:
           # if not then 
            flash("This file is unsafe and cannot be downloaded.") # Block the download and show a warning
            return redirect(url_for('index'))
    else:
        # If no scan result is found, block the download
        flash("File not scanned yet. Please scan the file before downloading.")
        return redirect(url_for('index'))

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS # checks if the file exension is in the ALLOWED EXTENSTION dictionary 

if __name__ == '__main__':
    if not os.path.exists(Config.UPLOAD_FOLDER):# checks if the uplaod folder exist
        os.makedirs(Config.UPLOAD_FOLDER)# if not then make one 
    app.run(debug=False)
