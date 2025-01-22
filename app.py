from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from firebase_admin import credentials, initialize_app, firestore, storage
import uuid
from datetime import datetime
from flask_mail import Mail, Message


# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'nikhilvarma.kandula@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'wcrd vrsa nmnq acqp'  # Replace with app-specific password
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

mail = Mail(app)


# Initialize Firebase Admin
cred = credentials.Certificate('engineeredPrompt.json')
firebase_app = initialize_app(cred, {
    'storageBucket': 'disharaengineeredprompt.appspot.com'  # Correct bucket name
})

# Firestore client
db = firestore.client()

# Firebase Storage bucket
bucket = storage.bucket()

# Helper function to get the users collection
def get_prompt_users_collection():
    return db.collection("users")


@app.route('/')
def home():
    """Render the home page, display prompts, and pass login status."""
    is_logged_in = session.get('logged_in', False)

    try:
        prompts_ref = db.collection('PRMTFILP').get()
        prompts = [{'id': prompt.id, **prompt.to_dict()} for prompt in prompts_ref]
    except Exception as e:
        print(f"Error fetching prompts: {e}")
        prompts = []

    return render_template('index.html', is_logged_in=is_logged_in, prompts=prompts)



@app.route('/signup.html')
def signup():
    """Render the signup page."""
    is_logged_in = session.get('logged_in', False)
    return render_template("signup.html", is_logged_in=is_logged_in)


@app.route('/signup-submit', methods=['POST'])
def signup_submit():
    """Handle user registration."""
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]
    full_name = request.form["full_name"]

    try:
        users_ref = get_prompt_users_collection()
        query = users_ref.where("email", "==", email).limit(1).get()

        if query:
            return render_template("signup.html", fail_message="User already exists.")

        if password != confirm_password:
            return render_template("signup.html", fail_message="Passwords do not match.")

        user_data = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "unique_id": str(uuid.uuid4()),
            "login_time": datetime.now()
        }
        users_ref.document(user_data["unique_id"]).set(user_data)
        return redirect("/login.html")
    except Exception as e:
        print(f"Error creating user: {e}")
        return render_template("signup.html", fail_message="An error occurred. Please try again.")


@app.route('/login.html')
def login():
    """Render the login page."""
    is_logged_in = session.get('logged_in', False)
    return render_template("login.html", is_logged_in=is_logged_in)

@app.route('/login', methods=['POST'])
def login_page():
    """Handle user login."""
    email = request.form["email"]
    password = request.form["password"]

    try:
        users_ref = get_prompt_users_collection()
        query = users_ref.where("email", "==", email).where("password", "==", password).limit(1).get()

        if not query:
            return render_template("login.html", fail_message="Invalid credentials.")

        session['logged_in'] = True
        session['user_id'] = query[0].id
        return redirect("/")
    except Exception as e:
        print(f"Error logging in: {e}")
        return render_template("login.html", fail_message="An error occurred. Please try again.")


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    return redirect("/login.html")


@app.route('/privacypolicy.html')
def privacy_policy():
    """Render the privacy policy page."""
    return render_template("privacypolicy.html")


@app.route('/termsofservice.html')
def terms_of_service():
    """Render the terms of service page."""
    return render_template("termsofservice.html")


@app.route('/submit_prompt', methods=['POST'])
def submit_prompt():
    """Handle the submission of a new prompt."""
    prompt_purpose = request.form['prompt_purpose']
    engineered_prompt = request.form['engineered_prompt']
    prompt_type = request.form['prompt_type']
    time_stamp = datetime.now()

    prompt_data = {
        'Prompt_Purpose': prompt_purpose,
        'Engineered_Prompt': engineered_prompt,
        'Prompt_Type': prompt_type,
        'time_stamp': time_stamp,
        'number_of_likes': 0
    }

    file = request.files.get('file_upload')
    if file:
        try:
            file_extension = file.filename.split('.')[-1]
            filename = f"{uuid.uuid4()}.{file_extension}"
            blob = bucket.blob(f'uploads/{filename}')
            blob.upload_from_file(file)
            blob.make_public()
            prompt_data['file_url'] = blob.public_url
        except Exception as e:
            print(f"Error uploading file: {e}")

    try:
        db.collection('PRMTFILP').add(prompt_data)
        return redirect("/")
    except Exception as e:
        print(f"Error adding prompt: {e}")
        return redirect("/")


@app.route('/like_prompt', methods=['POST'])
def like_prompt():
    """Handle likes for a prompt."""
    prompt_id = request.json.get('prompt_id')
    user_id = session.get('user_id')

    if not prompt_id or not user_id:
        return jsonify({'success': False, 'message': 'Invalid prompt ID or user ID'})

    try:
        prompt_ref = db.collection('PRMTFILP').document(prompt_id)
        prompt_doc = prompt_ref.get()

        if prompt_doc.exists:
            prompt_data = prompt_doc.to_dict()
            liked_by = prompt_data.get('liked_by', [])

            if user_id in liked_by:
                return jsonify({'success': False, 'message': 'You have already liked this prompt.'})

            current_likes = prompt_data.get('number_of_likes', 0)
            liked_by.append(user_id)

            prompt_ref.update({'number_of_likes': current_likes + 1, 'liked_by': liked_by})

            return jsonify({'success': True, 'updated_likes': current_likes + 1})

        return jsonify({'success': False, 'message': 'Prompt not found'})
    except Exception as e:
        print(f"Error updating likes: {e}")
        return jsonify({'success': False, 'message': 'An error occurred.'})


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    feedback = request.form.get('feedback', '').strip()
    user_email = request.form.get('email', '').strip()

    if not feedback:
        return jsonify({'success': False, 'message': 'Feedback cannot be empty'}), 400

    try:
        # Prepare the email
        subject = "New Feedback from Website"
        body = f"Feedback: {feedback}\n\nUser Email: {user_email or 'Not Provided'}"
        msg = Message(subject, recipients=['nikhilvarma.kandula@gmail.com'])  # Replace with your email
        msg.body = body

        # Send the email
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Feedback submitted successfully!'}), 200
    except Exception as e:
        print(f"Error sending feedback email: {e}")  # Logs the exception to the console
        return jsonify({'success': False, 'message': f"An error occurred: {e}"}), 500



if __name__ == '__main__':
    app.run(debug=True)
