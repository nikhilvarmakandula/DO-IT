from flask import Flask, render_template, request, redirect, url_for, jsonify
from firebase_admin import firestore, credentials, initialize_app
import uuid
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Initialize Firestore with provided credentials
cred = credentials.Certificate('engineeredPrompt.json')
firebase_app = initialize_app(cred)
db = firestore.client()


# Route to render index.html
@app.route('/')
def index():
    try:
        prompts_ref = db.collection('PRMTFILP').get()
        prompts = [{'id': prompt.id, **prompt.to_dict()} for prompt in prompts_ref]
        return render_template('index.html', prompts=prompts)
    except Exception as e:
        print(f"Error fetching prompts: {e}")
        return render_template('index.html', prompts=[])


@app.route('/privacypolicy.html')
def privacy_policy():
    return render_template("privacypolicy.html")


@app.route('/signup.html')
def signup():
    return render_template("signup.html")


@app.route('/signup-submit', methods=['POST'])
def signup_submit():
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]
    full_name = request.form["full_name"]

    try:
        users_ref = get_prompt_users_collection()
        query = users_ref.where("email", "==", email).limit(1)
        result = query.get()

        if len(result) > 0:
            return render_template("signup.html", fail_message="User already exists.")

        if password != confirm_password:
            return render_template("signup.html", fail_message="Passwords do not match. Please try again.")

        unique_id = str(uuid.uuid4())
        login_time = datetime.now()

        user_data = {
            "email": email,
            "password": password,
            "unique_id": unique_id,
            "full_name": full_name,
            "login_time": login_time
        }
        users_ref.document(unique_id).set(user_data)

        return redirect("/login.html")
    except Exception as e:
        print(f"Error creating user: {e}")
        return render_template("signup.html", fail_message="An error occurred. Please try again.")


@app.route('/login.html')
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login_page():
    email = request.form["email"]
    password = request.form["password"]

    try:
        users_ref = get_prompt_users_collection()
        query = users_ref.where("email", "==", email).where("password", "==", password).limit(1)
        result = query.get()

        if len(result) == 0:
            return render_template("login.html", fail_message="Invalid credentials. Please try again.")

        return redirect("/")
    except Exception as e:
        print(f"Error logging in: {e}")
        return render_template("login.html", fail_message="An error occurred. Please try again.")


@app.route('/logout')
def logout():
    return redirect("/login.html")


@app.route('/termsofservice.html')
def terms_of_service():
    return render_template("termsofservice.html")


@app.route('/submit_prompt', methods=['POST'])
def submit_prompt():
    
    prompt_purpose = request.form['prompt_purpose']
    engineered_prompt = request.form['engineered_prompt']
    time_stamp = datetime.now()

    prompt_data = {
        'Prompt_Purpose': prompt_purpose,
        'Engineered_Prompt': engineered_prompt,
        'time_stamp': time_stamp,
        'number_of_likes': 0  # Initialize likes
    }

    try:
        db.collection('PRMTFILP').add(prompt_data)
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error adding prompt: {e}")
        return redirect(url_for('index'))


@app.route('/like_prompt', methods=['POST'])
def like_prompt():
    prompt_id = request.json.get('prompt_id')
    user_id = request.json.get('user_id')  # Pass user_id from the frontend

    if not prompt_id or not user_id:
        return jsonify({'success': False, 'message': 'Invalid prompt ID or user ID'})

    try:
        # Fetch the prompt document
        prompt_ref = db.collection('PRMTFILP').document(prompt_id)
        prompt_doc = prompt_ref.get()

        if prompt_doc.exists:
            prompt_data = prompt_doc.to_dict()
            liked_by = prompt_data.get('liked_by', [])  # Get the array of users who liked

            # If user already liked, do nothing and return success with current likes
            if user_id in liked_by:
                return jsonify({'success': True, 'updated_likes': prompt_data.get('number_of_likes', 0)})

            # Increment likes and add user to liked_by
            current_likes = prompt_data.get('number_of_likes', 0)
            liked_by.append(user_id)  # Add user ID to the liked_by array

            # Update the document
            prompt_ref.update({
                'number_of_likes': current_likes + 1,
                'liked_by': liked_by
            })

            return jsonify({'success': True, 'updated_likes': current_likes + 1})

        else:
            return jsonify({'success': False, 'message': 'Prompt not found'})
    except Exception as e:
        print(f"Error updating likes: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while liking the prompt.'})


def get_prompt_users_collection():
    return db.collection("users")


if __name__ == '__main__':
    app.run(debug=True)