"""
Step 1: Have Clear Goals - Fast Version
"""
from .Program_Wide_Prompt import PROGRAM_WIDE_PROMPT

def handle_step1(user_input, history, goal, client):
    """
    Guides the user through Step 1: Have Clear Goals with faster progression
    """
    # System content with minimal coaching instructions
    system_content = f"""{PROGRAM_WIDE_PROMPT}

You are guiding the user through Step 1: Have Clear Goals.
The user's current goal is: {goal if goal else "Not yet defined"}

## Fast Goal Identification Guidelines

1. If the user mentions ANY specific goal that's reasonably clear, IMMEDIATELY confirm it and move to the next step.
   - As soon as you see a goal that's specific enough to work with, consider it valid
   - Don't insist on perfection - a workable goal is sufficient
   - Example valid goals: "finish the project by Friday", "improve team communication", "reduce errors by 10%"

2. If the user's input is too vague to be a goal (e.g., "I want to be better"), ask ONE clarifying question:
   - "Could you make that more specific? For example, what do you want to be better at?"
   - Once they respond with ANY clarification, accept it as their goal

3. If the user provides multiple goals, simply ask them to choose one:
   - "You've mentioned several goals. Which one would you like to focus on first?"
   - Accept whatever they choose immediately

4. As soon as you've identified a workable goal:
   - Include "STEP_COMPLETE" in your response (invisible to user)
   - Confirm with: "Goal confirmed: [user's goal]"
   - Immediately transition with: "Now, let's identify what obstacles might be in your way."

<evaluation>Keep this extremely brief - one sentence maximum.</evaluation>

The MOMENT you identify a specific, workable goal, confirm it and move on. Don't wait for multiple exchanges.
"""

    # Prepare the message history for Claude
    messages = []
    
    # Add conversation history
    if history:
        messages.extend(history)
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})

    # Limit the number of messages to avoid token limit issues
    if len(messages) > 10:
        messages = messages[-10:]
        
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
    
    # Check for goal confirmation markers - expanded to catch more variations
    is_complete = ("STEP_COMPLETE" in response or 
                   "Goal confirmed" in response or 
                   "goal is confirmed" in response or
                   "confirmed your goal" in response)
                   
    return response, is_complete, evaluation_summary


def extract_goal(response):
    """
    Extract the confirmed goal from the response text
    Modified to be more flexible in extracting goals
    """
    import re
    
    # Try several patterns to extract the goal
    patterns = [
        r'Goal confirmed: (.+?)[\.|\!]',
        r'goal is: (.+?)[\.|\!]',
        r'focusing on (.+?)[\.|\!]',
        r'aiming to (.+?)[\.|\!]'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            return match.group(1).strip()
    
    # Fallback method if patterns don't match
    if "Goal confirmed" in response:
        parts = response.split("Goal confirmed:")
        if len(parts) > 1:
            goal_part = parts[1].strip()
            # Extract until the end of sentence or first period
            end_index = goal_part.find('.')
            if end_index != -1:
                return goal_part[:end_index].strip()
            return goal_part.strip()
    
    return None  # Unable to extract goal