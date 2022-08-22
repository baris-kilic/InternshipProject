import flask
import pandas as pd

from joblib import load # Load the model from the file
import spacy            # NLP library

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


nlp = spacy.load('en_core_web_sm') # using small model for speed

app = flask.Flask(__name__)
app.config["DEBUG"] = True

model: KMeans           = load('./includes/new/kmeans.joblib')
df                      = pd.read_csv('./includes/new/kmeans.csv', sep=';')
vector: TfidfVectorizer = load('./includes/new/vectorizer.joblib')
reviews                 = pd.read_csv('./includes/review_sentiment.csv', sep=';')
reviews_df              = reviews.groupby('course_id').mean()

"""
Home page route
"""
@app.route('/', methods=['GET'])
def home():
    return flask.send_from_directory('.', 'index.html')

"""
Home page image route
"""
@app.route('/img/laptop-code-solid.svg', methods=['GET'])
def img():
    return flask.send_from_directory('./img/', 'laptop-code-solid.svg')


"""
Category selection page route
"""
@app.route('/cc.html', methods=['GET'])
def cat():
    return flask.send_from_directory('.', 'cc.html')

"""
Suggestion page route
"""
@app.route('/sg.html', methods=['GET'])
def sug():
    return flask.send_from_directory('.', 'sg.html')


"""
Prediction API route
"""
@app.route('/predict', methods=['POST'])
def predict():
    data = {'success': False} # Return JSON data as Python dictionary
    # If request is a POST request and requst has the necessary parameters
    if flask.request.method == 'POST' \
        and flask.request.form['topic'] \
        and flask.request.form['level'] \
        and flask.request.form['category']:
            
        # Get the parameters from the request
        course_name = flask.request.form['topic']
        level = flask.request.form['level']
        selected_category = flask.request.form['category']
        
        # Text preprocessing
        selected_category = selected_category.replace('_', ' ')
        selected_category = selected_category.lower()
        
        # Transform the course name into a vector
        course_vector = vector.transform([course_name])
        # Predict the course cluster
        course_cluster = model.predict(course_vector)[0]
        
        # If user not specified a level nor category
        if level == "Any" and selected_category.lower() == "all":
            similar_courses = df[df['name_cluster'] == course_cluster].sample(n=5, replace=True)
        # If user not specified a level but specified a category
        elif level == "Any" and selected_category.lower() != "all":
            similar_courses = df[df['category'] == selected_category][df['name_cluster'] == course_cluster].sample(n=5, replace=True)
        # If user specified a level and not a category
        elif level != "Any" and selected_category.lower() == "all":
            similar_courses = df[df['instructional_level'] == level][df['name_cluster'] == course_cluster].sample(n=5, replace=True)
        # If user specified a level and a category
        else:
            similar_courses = df[df['category'] == selected_category][df['instructional_level'] == level][df['name_cluster'] == course_cluster].sample(n=5, replace=True)

        # Drop duplicated results from the query
        similar_courses = similar_courses.drop_duplicates(subset='course_id', keep='first')

        # Add results to the data dictionary
        data['success'] = True
        data['similar_courses'] = similar_courses.to_dict('records')
        
        # iterate through the similar courses and add the average sentiment score to the data dictionary
        for similar_course in data['similar_courses']:
            # check if the course is in the reviews dataframe
            if similar_course['course_id'] in reviews_df.index:
                similar_course['review_score'] = reviews_df.loc[similar_course['course_id']].to_dict()

    else:
        data['error'] = 'Please enter all fields'
    return flask.jsonify(data)

app.run()