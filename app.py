from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import anthropic
from steps.step1 import handle_step1
from steps.step2 import handle_step2
from steps.step3 import handle_step3
from steps.step4 import handle_step4
from steps.step5 import handle_step5
import re
import os
import json
from datetime import timedelta

# Environment variables for configuration
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
    print("Environment variables loaded from .env file")
except ImportError:
    print("dotenv package not available, using default environment variables")
except Exception as e:
    print(f"Error loading environment variables: {str(e)}")

def configure_sessions(app):
    """
    Configure sessions for Vercel deployment - serverless environment requires simpler session handling
    """
    # For serverless, we use simpler cookie-based sessions with a secret key
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'YCTk4viYiohqPmqQUg85hRezAVUdW47qWsuONrntUAY')
    # These settings help with cookie size in serverless environments
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    return app

app = Flask(__name__)
app = configure_sessions(app)  # Configure sessions
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files
CORS(app)

# Get API key from environment variable
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY environment variable is not set. API calls will fail.")
    ANTHROPIC_API_KEY = "MISSING_API_KEY"  # This will cause a clear error if API is called

try:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("Successfully initialized Anthropic client")
except Exception as e:
    print(f"Error initializing Anthropic client: {str(e)}")

# Map step numbers to their functions
step_functions = {
    1: handle_step1,
    2: handle_step2,
    3: handle_step3,
    4: handle_step4,
    5: handle_step5
}

# Step names for display
steps = [
    {"number": 1, "name": "Have Clear Goals", "description": "Define a specific, measurable goal"},
    {"number": 2, "name": "Identify Problems", "description": "Identify obstacles preventing goal achievement"},
    {"number": 3, "name": "Diagnose Root Causes", "description": "Find the underlying reasons for problems"},
    {"number": 4, "name": "Design a Plan", "description": "Create an actionable plan to address root causes"},
    {"number": 5, "name": "Push Through to Completion", "description": "Establish execution habits and accountability"}
]

def truncate_history(history, max_messages=10):
    """Truncate conversation history to avoid token limits"""
    if len(history) > max_messages:
        # Keep the most recent messages
        return history[-max_messages:]
    return history

def generate_email_summary(session_data):
    """
    Generates an email summary of the 5-step process results
    that can be shared with colleagues or management.
    
    Args:
        session_data: Dictionary containing the session data including
                     goal, completed steps, and evaluation summaries
    
    Returns:
        str: Formatted email content
    """
    goal = session_data.get('goal', 'Not specified')
    
    # Get evaluation summaries from each step
    step_evaluations = session_data.get('step_evaluations', {})
    
    # Format the email
    email_content = f"""
Subject: Process Improvement Analysis: {goal}

Dear Team,

I recently conducted a structured analysis of our current process related to: "{goal}". 
I'd like to share the findings to help us identify common pain points and collaborate on improvements.

## Goal
{goal}

## Key Problems Identified
{step_evaluations.get('2', 'No problems identified yet.')}

## Root Causes
{step_evaluations.get('3', 'Root causes not analyzed yet.')}

## Proposed Plan
{step_evaluations.get('4', 'Plan not developed yet.')}

## Implementation Strategy
{step_evaluations.get('5', 'Implementation strategy not developed yet.')}

I believe addressing these issues could significantly improve our workflow efficiency and reduce frustration. 
I'd appreciate your input on these findings and any additional pain points you've experienced that might not be captured here.

Could you please review and let me know:
1. Do these findings align with your experience?
2. Are there additional issues you've encountered?
3. Do you have any suggestions for the proposed solutions?

Thank you for your time and collaboration.

Regards,
[Your Name]
"""
    return email_content

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Initialize session if not already set
        if 'current_step' not in session:
            print("Initializing new session")
            session['current_step'] = 1
            session['completed_steps'] = []
            session['history'] = []
            session['goal'] = None
            session['step_evaluations'] = {}

        data = request.get_json()
        user_input = data.get('user_input', '')
        
        # Get and truncate history to manage token count
        history = truncate_history(session.get('history', []))
        goal = session.get('goal')

        current_step = session['current_step']
        step_function = step_functions[current_step]
        
        # Handle special case for first message - we'll auto-generate a welcome message
        if len(history) == 0 and user_input.lower() in ['hi', 'hello', 'hey', 'start']:
            welcome_message = (
                "STEP 1: HAVE CLEAR GOALS\n\n"
                "Hi there! I'm excited to guide you through a powerful process that's helped countless people achieve their goals. "
                "We'll be using Ray Dalio's proven 5-step method:\n\n"
                "1. Have Clear Goals\n"
                "2. Identify and Don't Tolerate Problems\n"
                "3. Diagnose Problems to Get at Their Root Causes\n"
                "4. Design a Plan\n"
                "5. Push Through to Completion\n\n"
                "Let's start with step 1: What goal would you like to focus on today? "
                "Think about something meaningful you're working toward. The more specific you can be, the better we can work together.\n\n"
                "CURRENT STEP: 1 - HAVE CLEAR GOALS"
            )
            
            # Update conversation history with full message including markers (for system use)
            history.append({'role': 'user', 'content': user_input})
            history.append({'role': 'assistant', 'content': welcome_message})
            session['history'] = history
            
            # Clean welcome message for user display
            cleaned_welcome = remove_step_headers(welcome_message)
            
            return jsonify({
                'main_response': cleaned_welcome,
                'evaluation_summary': '',
                'completed_steps': [],
                'current_step': 1,
                'step_info': get_step_info(1)
            })
        
        # Normal flow for all other messages
        main_response, is_complete, evaluation_summary = step_function(user_input, history, goal, client)

        # Update conversation history with full response including markers (for system use)
        history.append({'role': 'user', 'content': user_input})
        history.append({'role': 'assistant', 'content': main_response})
        session['history'] = history

        # Store evaluation summary for this step if one was provided
        if evaluation_summary:
            if 'step_evaluations' not in session:
                session['step_evaluations'] = {}
            # Store the step as a string key to avoid int/str comparison issues in session serialization
            session['step_evaluations'][str(current_step)] = evaluation_summary

        # Handle step completion
        if is_complete:
            if current_step not in session['completed_steps']:
                session['completed_steps'].append(current_step)
            if current_step == 1:
                session['goal'] = extract_goal(main_response)
            if current_step < 5:
                session['current_step'] = current_step + 1

        # Prepare data for frontend
        completed_steps = [
            {
                'step': i, 
                'name': next((s['name'] for s in steps if s['number'] == i), f"Step {i}"),
                'description': next((s['description'] for s in steps if s['number'] == i), ""),
                'goal': session['goal'] if i == 1 else None
            }
            for i in session['completed_steps']
        ]
        
        # Clean response for user display - remove step headers and STEP_COMPLETE marker
        cleaned_response = remove_step_headers(main_response)
        # Also remove the STEP_COMPLETE marker
        cleaned_response = cleaned_response.replace("STEP_COMPLETE", "")
        # Clean up any extra whitespace created by removing markers
        cleaned_response = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response).strip()

        return jsonify({
            'main_response': cleaned_response,
            'evaluation_summary': evaluation_summary,
            'completed_steps': completed_steps,
            'current_step': session['current_step'],
            'step_info': get_step_info(session['current_step'])
        })
    except Exception as e:
        # Handle any errors
        error_message = f"An error occurred: {str(e)}"
        print(error_message)  # Log the error
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        
        # Create a more user-friendly message
        user_error_message = "I encountered an error. Please try again or reset the conversation."
        
        # Check for common error types
        if "token" in str(e).lower() or "exceed" in str(e).lower() or "overload" in str(e).lower():
            user_error_message = "The conversation has become too long. Please reset the conversation to continue."
        elif "api" in str(e).lower() or "anthropic" in str(e).lower() or "key" in str(e).lower():
            user_error_message = "There was an issue connecting to the AI service. Please check server configuration."
        
        return jsonify({
            'main_response': user_error_message,
            'evaluation_summary': error_message,
            'completed_steps': session.get('completed_steps', []),
            'current_step': session.get('current_step', 1),
            'step_info': get_step_info(session.get('current_step', 1))
        }), 500

def get_step_info(step_number):
    """Returns information about the current step"""
    step_info = next((s for s in steps if s['number'] == step_number), None)
    if not step_info:
        return {"number": step_number, "name": f"Step {step_number}", "description": ""}
    return step_info

@app.route('/set_step', methods=['POST'])
def set_step():
    data = request.get_json()
    step = data['step']
    
    # Ensure they can only go to a completed step or the current step
    if step in session['completed_steps'] or step == session['current_step']:
        session['current_step'] = step
        return jsonify({
            'status': 'success',
            'current_step': step,
            'step_info': get_step_info(step)
        })
    return jsonify({'status': 'error', 'message': 'Step not completed yet'}), 403

@app.route('/reset', methods=['POST'])
def reset_conversation():
    # Clear all session data
    session.clear()
    if session.get('_flashes'):
        del session['_flashes']
    # Reinitialize session
    session['current_step'] = 1
    session['completed_steps'] = []
    session['history'] = []
    session['goal'] = None
    session['step_evaluations'] = {}
    return jsonify({
        'status': 'success',
        'current_step': 1,
        'step_info': get_step_info(1)
    })

@app.route('/get_summary', methods=['GET'])
def get_summary():
    """Endpoint to generate and return an email summary of the process"""
    # Create a dictionary to store all evaluations by step
    step_evaluations = {}
    
    # Get completed steps and their evaluations
    if 'step_evaluations' in session:
        step_evaluations = session['step_evaluations']
    
    # Create summary data
    summary_data = {
        'goal': session.get('goal', 'Not specified'),
        'step_evaluations': step_evaluations
    }
    
    # Generate the email content
    email_content = generate_email_summary(summary_data)
    
    return jsonify({
        'email_content': email_content
    })

@app.route('/progress', methods=['GET'])
def get_progress():
    """Returns the current progress through the 5-step process"""
    return jsonify({
        'current_step': session.get('current_step', 1),
        'completed_steps': session.get('completed_steps', []),
        'goal': session.get('goal', None),
        'step_info': get_step_info(session.get('current_step', 1)),
        'all_steps': steps
    })

@app.route('/')
def serve_frontend():
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        print(f"Error serving index.html: {str(e)}")
        # Return a basic HTML response in case the static file can't be found
        return '<html><body><h1>5-Step Process</h1><p>There was an error loading the application. Please check the server logs.</p></body></html>'
    
@app.route('/api/health')
def health_check():
    """Simple health check endpoint to verify API is working"""
    # Collect diagnostic information
    import sys
    import platform
    
    # Check if we can connect to Anthropic API
    api_status = "ok"
    try:
        # Just do a simple API check
        _ = client.models.list()
    except Exception as e:
        api_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok",
        "version": "1.0",
        "environment": os.environ.get('VERCEL_ENV', 'development'),
        "python_version": sys.version,
        "platform": platform.platform(),
        "api_status": api_status,
        "env_vars": {k: "***" for k in os.environ if k.startswith("ANTHROPIC") or k == "SECRET_KEY"}
    })

def remove_step_headers(response):
    """Remove STEP headers and footers from the response"""
    # Remove the header (STEP X: TITLE)
    header_pattern = r'^STEP \d+: [A-Z\s]+'
    response = re.sub(header_pattern, '', response)
    
    # Remove the footer (CURRENT STEP: X - TITLE)
    footer_pattern = r'CURRENT STEP: \d+ - [A-Z\s]+$'
    response = re.sub(footer_pattern, '', response)
    
    # Trim any extra whitespace
    return response.strip()

def extract_goal(response):
    # Look for the specific pattern with "Goal confirmed:" followed by text and ending with period or "Moving"
    match = re.search(r'Goal confirmed: (.+?)(?:\.|\. Moving)', response)
    if match:
        return match.group(1).strip()
        
    # Fallback if the exact pattern isn't found
    if "Goal confirmed:" in response:
        parts = response.split("Goal confirmed:")
        if len(parts) > 1:
            goal_part = parts[1].strip()
            # Extract until the end of sentence or first period
            end_index = goal_part.find('.')
            if end_index != -1:
                return goal_part[:end_index].strip()
            # If no period, try finding "Moving to next step"
            end_index = goal_part.find('Moving to next step')
            if end_index != -1:
                return goal_part[:end_index].strip()
            return goal_part.strip()
    return None

# The following makes the app work both locally and on Vercel
if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
# This is needed for Vercel deployment
# Do not remove - Vercel uses this to import your Flask app
application = app