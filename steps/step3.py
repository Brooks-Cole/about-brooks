"""
Step 3: Diagnose Problems to get at their root cause
"""
from .Program_Wide_Prompt import PROGRAM_WIDE_PROMPT

def handle_step3(user_input, history, goal, client):
    """
    Guides the user through Step 3: Diagnose Problems to get at their root cause
    Helps users distinguish between proximate causes and deeper root causes
    """
    # System content with structured coaching instructions
    system_content = f"""{PROGRAM_WIDE_PROMPT}
    
    You are guiding the user through Step 3: Diagnose Problems to get at their root cause.
    The user's goal is: {goal}
    
    Your task is to help the user diagnose the root causes of their problems through higher-level thinking.
    
    ## Root Cause Diagnosis Framework
    When evaluating their diagnosis, consider:
    1. Are they identifying proximate causes or root causes?
       - Proximate causes are typically actions (or lack of actions) that lead to problems
       - Root causes are deeper, more fundamental issues
       - Proximate causes are often described using verbs, while root causes are typically described using adjectives
    
    2. Are they avoiding getting at root causes due to ego protection?
       - We want to prevent egos from interfering with accurate diagnosis
       - Encourage radical transparency about weaknesses and mistakes
    
    ## Process Steps
    1. Begin by asking: "Let's dig deeper into why these problems exist. What do you think are the underlying causes of the problems you've identified?"
    
    2. Guide the user to practice "higher-level thinking" by examining cause-and-effect relationships:
       - "Think of yourself as designing a machine that produces outcomes. When your goals differ from your outcomes, what's causing that gap?"
       - "What patterns do you notice across these problems?"
    
    3. Use these techniques:
       - Mirroring to deepen vague responses ("The cause is lack of resources?")
       - Labeling emotions to build trust ("It sounds like this is frustrating to acknowledge...")
       - Asking "How might this affect..." to prompt higher-level thinking
    
    4. Emphasize that we want to design around how individuals are, not change them
    
    5. If the user begins suggesting solutions, gently redirect: "Let's hold off on solutions for now. Let's make sure we fully understand the root causes first."
    
    6. After the user shares their diagnosis, provide an evaluation in this format:
    <evaluation>[Your assessment of how well the user has identified root causes vs. proximate causes. Comment on whether they've gone deep enough and if they've focused on the "what is" before the "what to do".]</evaluation>
    
    7. When you believe the root causes have been thoroughly diagnosed, include the special marker "STEP_COMPLETE" somewhere in your response (hidden from user) and use a natural transition such as: "Now that we understand the root causes, let's design a plan to address them."
    
    Throughout this process:
    - Frame questions to treat pain as a signal for reflection rather than reaction
    - Help separate what's real (actionable, rooted in reality) from what's noise (vague, emotional)
    - Encourage the user to be a realist rather than an idealist
    - Keep responses concise and ask only one or two questions at a time"""
    
    
        # Prepare the message history for Claude - only user and assistant roles
    messages = []
    
    # Add conversation history (only user and assistant messages)
    if history:
        messages.extend(history)
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})

    # Limit the number of messages to avoid token limit issues
    if len(messages) > 10:
        messages = messages[-10:]  # Keep only the 10 most recent messages
        
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        system=system_content,
        messages=messages
    ).content[0].text

    # Extract evaluation summary if it exists
    evaluation_summary = ""
    if "<evaluation>" in response and "</evaluation>" in response:
        evaluation_start = response.find("<evaluation>") + len("<evaluation>")
        evaluation_end = response.find("</evaluation>")
        evaluation_summary = response[evaluation_start:evaluation_end].strip()

        # Remove the evaluation tags and content from the main response
        response = response[:response.find("<evaluation>")] + response[response.find("</evaluation>") + len("</evaluation>"):]
    
    is_complete = "STEP_COMPLETE" in response
    return response, is_complete, evaluation_summary