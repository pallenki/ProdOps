from flask import Flask, request, jsonify, Blueprint
import os
from werkzeug.utils import secure_filename
from transformers import pipeline
app = Flask(__name__)
main = Blueprint('main', __name__)
app.config['UPLOAD_FOLDER'] = 'uploaded_transcripts'
app.config['INSIGHTS_FILE'] = 'insights.txt'  # File to store unique insights

# Assuming the model is suitable for question-answering
qa_extractor = pipeline("question-answering")

def load_existing_insights():
    try:
        with open(app.config['INSIGHTS_FILE'], 'r') as file:
            existing_insights = set(file.read().splitlines())
        return existing_insights
    except FileNotFoundError:
        return set()

def save_insights(new_insights):
    with open(app.config['INSIGHTS_FILE'], 'a') as file:
        for insight in new_insights:
            file.write(f"{insight}\n")

def filter_insights(new_insights):
    existing_insights = load_existing_insights()
    unique_insights = set(new_insights) - existing_insights
    return list(unique_insights)

def extract_insights(transcript):
    try:
        pain_points = qa_extractor(question="What are the top three pain points?", context=transcript)
        product_solutions = qa_extractor(question="What ideal product solutions are suggested?", context=transcript)
        desired_outcomes = qa_extractor(question="What outcomes are expected by the customer?", context=transcript)
        return {
            'pain_points': pain_points['answer'],
            'product_solutions': product_solutions['answer'],
            'desired_outcomes': desired_outcomes['answer']
        }
    except Exception as e:
        print(f"Error processing transcript: {e}")
        return {}

def aggregate_insights(all_insights):
    # Dictionary to hold combined insights
    combined_insights = {
        'pain_points': {},
        'product_solutions': {},
        'desired_outcomes': {}
    }

    # Loop through all insights from each interview
    for insights in all_insights:
        for category in combined_insights:
            # Split insights into individual points, assuming they are comma-separated
            points = insights.get(category, '').split(', ')
            for point in points:
                if point in combined_insights[category]:
                    combined_insights[category][point] += 1
                else:
                    combined_insights[category][point] = 1

    # Filter to retain only unique or significantly mentioned insights
    # for category in combined_insights:
    #     # Select points mentioned more than once or unique insightful points
    #     combined_insights[category] = {point: count for point, count in combined_insights[category].items() if count > 1}

    return combined_insights


@main.route('/upload-and-process', methods=['POST'])
def upload_and_process():
    files = request.files.getlist('file')
    all_insights = []
    #aggregated_insights = []
    for file in files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            transcript = f.read()
        insights = extract_insights(transcript)
        print('Insights: ', insights)
        all_insights.append(insights)
    
    # Aggregate and analyze insights across all files
    aggregated_insights = aggregate_insights(all_insights)
    # Save or process aggregated insights
    return jsonify({'aggregated_insights': aggregated_insights})

if __name__ == '__main__':
    app.run(debug=True)
