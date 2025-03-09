"""
Step 2: Identify and Don't Tolerate Problems
"""
from .Program_Wide_Prompt import PROGRAM_WIDE_PROMPT

def handle_step2(user_input, history, goal, client):
    """
    Guides the user through Step 2: Identify Problems
    Helps users identify specific problems standing in the way of their goal,
    focusing on what causes the most pain
    """
    # Determine the coaching stage based on conversation history
    current_stage = determine_coaching_stage(history)
    
    # System content with streamlined coaching instructions
    system_content = f"""{PROGRAM_WIDE_PROMPT}

You are guiding the user through Step 2: Identify Problems.
The user's goal is: {goal}

## Current Coaching Stage: {current_stage}

Your goal is to help the user identify the key pain points that stand in the way of achieving their goal. Focus on the most significant problems rather than trying to be exhaustive.

## Core Problem Identification Techniques

1. Pain-Point Focus:
   - Guide the user to identify what causes the most frustration or difficulty
   - Example: "What aspects of this situation cause you the most stress or frustration?"
   - Example: "Where do you feel you're wasting the most time or energy?"

2. Impact Assessment:
   - Help the user recognize which problems have the greatest impact
   - Example: "Which of these issues has the biggest effect on your ability to reach your goal?"
   - Example: "If you could solve just one aspect of this problem, which would make the biggest difference?"

3. Root vs. Symptom Differentiation:
   - Help distinguish between surface issues and deeper problems
   - Example: "Do you think that's the core issue, or a symptom of something deeper?"
   - Example: "Have you noticed patterns across these different challenges?"

{get_stage_instructions(current_stage)}

After the user has identified their key pain points, provide an evaluation in this format:
<evaluation>[Your assessment of the most significant problems identified. Focus on 2-3 key issues that appear to cause the most pain and have the greatest impact on the user's goal. Note which seem to be root issues versus symptoms.]</evaluation>

Remember: We're seeking clarity on what's causing the most pain, not building an exhaustive list of every possible problem.

IMPORTANT:
- When you have identified the 2-3 most significant pain points, include "STEP_COMPLETE" in your response (invisible to user) and say something like "Now that we've identified your key challenges, let's explore why these problems exist."
- Use natural transitions between steps that feel conversational, not formulaic.

Throughout this process:
- Keep responses conversational and empathetic
- Focus on problems that truly block the user's progress toward their goal
- Remember that pain is a signal - help the user see it as useful information rather than something to avoid
- Listen for emotional indicators that suggest where the real pain points lie"""

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
    
    # Check for step completion markers
    is_complete = "STEP_COMPLETE" in response or "Moving to next step" in response
    return response, is_complete, evaluation_summary


def determine_coaching_stage(history):
    """
    Determines the current coaching stage based on conversation history - simplified
    for faster progression
    """
    # If no history or very little history, we're at the beginning
    if not history or len(history) < 3:
        return "initial_question"
    
    # Count user messages to determine progress - accelerated
    user_messages = [msg for msg in history if msg.get('role') == 'user']
    
    # Simplified progression based on message count
    if len(user_messages) <= 1:
        return "initial_question"
    elif len(user_messages) <= 2:
        return "problem_exploration"
    else:
        return "problem_summarization"


def get_stage_instructions(stage):
    """
    Returns specific coaching instructions based on the current stage - streamlined
    """
    instructions = {
        "initial_question": """
## Problem Identification - Initial Stage
Begin with a focused question about the main obstacles:

"Let's identify what's getting in the way of your goal. What are the biggest challenges or pain points you're experiencing right now?"

Wait for the user's response before asking follow-up questions.
""",
        "problem_exploration": """
## Problem Identification - Exploration Stage
Now that the user has shared initial problems, help them prioritize:

"Of the challenges you've mentioned, which one causes you the most frustration or has the biggest impact on achieving your goal?"

Follow up with: "Are these issues more about [select one relevant to their situation: people/process/tools/knowledge/time]?"

This helps focus on the nature of the core problems.
""",
        "problem_summarization": """
## Problem Identification - Summarization Stage

Synthesize what you've learned into 2-3 key problems: 
"Based on what you've shared, it sounds like these are your main challenges..."

Check if your summary resonates: "Have I captured your biggest pain points correctly, or is there something more significant I've missed?"

After the user confirms, include "STEP_COMPLETE" in your response (invisible to user) and transition naturally:
"Now that we understand what's causing you the most pain, let's explore why these problems exist."
"""
    }
    
    return instructions.get(stage, instructions["initial_question"])