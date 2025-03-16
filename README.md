# Brooks' Personal AI Chatbot

A personal AI chatbot that represents Brooks and can answer questions about his background, interests, and projects. Perfect for linking to social media or dating profiles to give people a way to learn more about you.

## Features

- Clean, mobile-friendly chat interface
- Conversational AI powered by Claude
- Represents your personality and interests accurately
- Easy to deploy on Vercel
- Simple to customize with your own information

## Project Structure

```
personal-chatbot/
│
├── app.py                  # Main Flask application
├── static/                 # Static files directory
│   ├── index.html          # Frontend HTML
│   ├── styles.css          # CSS styles
│   └── script.js           # Frontend JavaScript
├── utils/
│   └── personal_profile.py # Your personal information
├── prompts/
│   └── system_prompt.py    # System prompt for Claude
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- An Anthropic API key with access to Claude

### Local Development

1. Clone the repository:
   ```
   git clone <your-repo-url>
   cd personal-chatbot
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

### Troubleshooting

#### ImportError: "Import 'dotenv' could not be resolved"

If you see this error in your IDE:

1. Make sure you've installed python-dotenv:
   ```
   pip install python-dotenv
   ```

2. If using VSCode:
   - Select the correct Python interpreter (Command Palette > Python: Select Interpreter)
   - Restart VSCode
   - Run `check_dotenv.py` to verify installation

3. The app has a fallback mechanism to install the package automatically

4. Customize your personal profile:
   - Edit `utils/personal_profile.py` with your information
   - Update the social media links in `static/index.html`
   - Modify the styling in `static/styles.css` if desired

5. Run the application:
   ```
   python app.py
   ```

6. Visit `http://localhost:5000` in your browser to test the chatbot

### Deploying to Vercel

1. Install Vercel CLI:
   ```
   npm install -g vercel
   ```

2. Create a `vercel.json` file in the root directory:
   ```json
   {
     "version": 2,
     "builds": [
       { "src": "app.py", "use": "@vercel/python" }
     ],
     "routes": [
       { "src": "/(.*)", "dest": "app.py" }
     ],
     "env": {
       "ANTHROPIC_API_KEY": "@anthropic_api_key"
     }
   }
   ```

3. Set up your environment variable in Vercel:
   ```
   vercel secrets add anthropic_api_key your_anthropic_api_key_here
   ```

4. Deploy to Vercel:
   ```
   vercel
   ```

## Customization

### Changing Your Profile Information

Edit the `PERSONAL_PROFILE` dictionary in `utils/personal_profile.py` to include your personal information. The system prompt will automatically be updated based on this data.

### Updating the Interface

- Modify `static/index.html` to change the layout and add your photo
- Edit `static/styles.css` to change colors, fonts, and styling
- Update the social media links in the footer section of `index.html`

### Changing the AI Model

By default, the application uses `claude-3-sonnet-20240229`. You can change this to any compatible Claude model by editing the `model` parameter in the `client.messages.create()` call in `app.py`.

## Usage Tips

- Link to your deployed chatbot from your Instagram, dating profiles, or other social media
- Include a QR code to your chatbot on your business card
- Update your personal_profile.py as you develop new interests or complete projects
- Review conversations and feedback to improve the system prompt over time

## License

This project is licensed under the MIT License - see the LICENSE file for details.