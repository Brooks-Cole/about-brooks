# prompts/slowburnjokes.py

def get_joke_prompt(joke_name, stage):
    """
    Returns the prompt segment for a specific joke and stage.

    Args:
        joke_name (str): The name of the joke (e.g., 'weighbeforeyoupay').
        stage (int): The current stage of the joke (0 = hint, 3 = punchline).

    Returns:
        str: The prompt segment for the given joke and stage.
    """
    jokes = {
        "weighbeforeyoupay": {
            0: "Occasionally mention travel or flying casually. E.g., 'Love travel, but those flights can be a lot, huh?'",
            1: "Subtly bring up airline frustrations. E.g., 'Airlines charge for everything—makes you want to pack light!'",
            2: "Hint at a solution. E.g., 'Maybe there’s a fair way to fix airline chaos—something clever.'",
            3: "Deliver the punchline: 'Introducing WeighBeforeYouPay! Tell complainers to march around DC—after a few laps, they’ll slim down, and we’re all good!'"
        },
        "puppypals": {
            0: "Casually mention dogs. E.g., 'Are you a dog person? I bet you’d sneak in some puppy cuddles.'",
            1: "Introduce temporary puppy love. E.g., 'Too bad there’s no puppy rental service for quick cuddles!'",
            2: "Mention the owner’s side. E.g., 'Puppy owners could use a break—those little chaos agents need daycare!'",
            3: "Punchline: 'PuppyPals! Rent puppies to cuddlers and daycare them for owners—win-win, and puppies get all the love!'"
        }
    }
    return jokes.get(joke_name, {}).get(stage, "")