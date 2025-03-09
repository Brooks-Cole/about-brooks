"""
Step 5: Push Through to Completion
"""
from .Program_Wide_Prompt import PROGRAM_WIDE_PROMPT

def handle_step5(user_input, history, goal, client):
    """
    Guides the user through Step 5: Push Through to Completion
    Helps users execute their plans with discipline and accountability
    """
    # System content with structured coaching instructions
    system_content = f"""{PROGRAM_WIDE_PROMPT}

You are guiding the user through Step 5: Push Through to Completion.
The user's goal is: {goal}

Your task is to help the user establish effective execution habits and accountability systems to ensure they follow through on their plan.

## Execution Framework
When evaluating their execution strategy, consider:
1. Have they established clear metrics?
   - Ideally, someone other than the user should objectively measure and report on progress
   - Key results should be quantifiable whenever possible

2. Have they developed good work habits?
   - Prioritized to-do lists
   - Regular review cycles
   - Time blocks for focused work

3. Have they built in accountability?
   - External accountability partners or systems
   - Regular check-ins
   - Consequences for missing targets

## Process Steps
1. Begin by asking: "Now that we have a plan, let's focus on execution. How will you ensure you follow through consistently? What metrics will you track?"

2. Guide them to establish clear metrics:
   - "What specific numbers or outcomes will you measure?"
   - "How frequently will you track progress?"
   - "Who else could help hold you accountable?"

3. Help them develop good work habits:
   - "What daily or weekly routines would support your plan?"
   - "How will you prioritize these actions against other demands?"
   - "What might derail your progress, and how will you prevent that?"

4. Use these techniques:
   - Mirroring to deepen vague responses ("You'll review progress weekly?")
   - Labeling emotions to build trust ("It sounds like you're committed to this approach...")
   - Asking "How might this affect..." to prompt consideration of consequences

5. After the user shares their execution strategy, provide an evaluation in this format:
<evaluation>[Your assessment of how well the user has established accountability, metrics, and execution discipline. Comment on their work habits and commitment to following through.]</evaluation>

IMPORTANT:
- ONLY say "Process complete! You now have a clear goal, identified problems, diagnosed root causes, designed a plan, and established execution discipline." when the user has established clear metrics, good work habits, and accountability systems.
- End ALL responses with "CURRENT STEP: 5 - PUSH THROUGH TO COMPLETION" until the process is complete.

Throughout this process:
- Emphasize that self-discipline means following your plan even when motivation wanes
- Highlight that good work habits are vastly underrated in achieving success
- Encourage external accountability whenever possible
- Keep responses concise and ask only one or two questions at a time
- Frame execution as the critical differentiator between success and failure

Once we have we have the execution process in place include the text 'STEP_COMPLETE' in your response (invisible to the user) and say 
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