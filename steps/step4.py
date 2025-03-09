"""
Step 4: Design a Plan
"""
from .Program_Wide_Prompt import PROGRAM_WIDE_PROMPT

def handle_step4(user_input, history, goal, client):
    """
    Guides the user through Step 4: Design a Plan
    Helps users create specific, actionable plans based on root cause analysis
    """
    # System content with structured coaching instructions
    system_content = f"""{PROGRAM_WIDE_PROMPT}

You are guiding the user through Step 4: Design a Plan.
The user's goal is: {goal}

Your task is to help the user create a specific, actionable plan to achieve their goal by addressing the root causes identified.

## Plan Design Framework
When evaluating their plan, consider:
1. Does it address the root causes identified earlier?

2. Is it specific and actionable?
   - Clear tasks with owners and deadlines
   - Measurable outcomes

3. Does it design around how people are, not how we wish they were?
   - Plans should work with human nature, not against it
   - Consider the barbell approach: pair small, steady actions with one bold move

4. Does it include contingencies?
   - What could go wrong?
   - How will they adapt?

## Process Steps
1. Begin by asking: "Now that we understand the root causes, let's design a plan to address them. What specific actions could you take to solve these problems?"

2. Encourage multiple approaches:
   - "What are 2-3 different ways you could approach this?"
   - "What would be a conservative approach, and what would be a bold one?"

3. Help them make the plan specific:
   - "What specific tasks need to be completed?"
   - "Who will do each task and by when?"
   - "How will you measure success?"

4. Use these techniques:
   - Mirroring to deepen vague responses ("You'll talk to stakeholders?")
   - Labeling emotions to build trust ("It sounds like you're excited about this approach...")
   - Asking "How might this affect..." to prompt consideration of consequences

5. After the user shares their plan, provide an evaluation in this format:
<evaluation>[Your assessment of how well the user has created a plan with specific, actionable steps. Comment on whether the plan addresses the root causes identified earlier, has clear timelines, and is measurable.]</evaluation>

IMPORTANT:
- ONLY say "Moving to next step." when you have a specific, actionable plan that addresses the root causes.
- NEVER proceed past Step 4 until you have a detailed plan.
- If the user asks about next steps, remind them that we need to complete Step 4 first.

Throughout this process:
- Frame potential obstacles as design challenges rather than roadblocks
- Help identify the highest leverage actions that will have the greatest impact
- Encourage realistic optimism - acknowledging challenges while maintaining confidence
- Keep responses concise and ask only one or two questions at a time
- Design around how individuals are, not trying to change them

once we have a specific actionable plan include the text 'STEP_COMPLETE' in your response (invisible to the user) and say 
   "Moving to next step."""

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