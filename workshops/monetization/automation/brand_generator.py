#!/usr/bin/env python3
"""
Human-First Brand Generator
Creates authentic-sounding brand identities that avoid AI slop detection
"""

import random

def generate_human_brands():
    """Generate 10 brand options that sound like real humans made them"""
    
    brands = [
        {
            "name": "CodeBrews",
            "username": "codebrews",
            "email": "codebrews@proton.me",
            "display": "CodeBrews",
            "bio": "Coffee-fueled coding tips ☕ | Daily wisdom from the dev grind",
            "vibe": "Casual, relatable, programmer culture",
            "why": "Portmanteau of code + brews (coffee). Feels like a real dev sharing tips over coffee."
        },
        {
            "name": "DevKitchen",
            "username": "devkitchen",
            "email": "devkitchen@proton.me",
            "display": "Dev Kitchen",
            "bio": "Cooking up code tutorials daily 👨‍🍳 | Fresh ideas, hot takes",
            "vibe": "Friendly, approachable, metaphor-based",
            "why": "Kitchen = where things are made. Implies craftsmanship, not automation."
        },
        {
            "name": "MindForge",
            "username": "mindforge",
            "email": "mindforge@proton.me",
            "display": "MindForge",
            "bio": "Forging sharper dev minds | Daily code wisdom ⚒️",
            "vibe": "Craftsmanship, mastery, skill-building",
            "why": "Forge = craft/build. Implies human skill development."
        },
        {
            "name": "PixelPioneer",
            "username": "pixelpioneer",
            "email": "pixelpioneer@proton.me",
            "display": "Pixel Pioneer",
            "bio": "Exploring the code frontier 🚀 | Daily dev discoveries",
            "vibe": "Adventurous, exploratory, human journey",
            "why": "Alliteration + pioneer implies human exploration."
        },
        {
            "name": "AlgoAlley",
            "username": "algoalley",
            "email": "algoalley@proton.me",
            "display": "Algo Alley",
            "bio": "Your shortcut to better algorithms 🛣️ | Quick tips daily",
            "vibe": "Streetwise, insider knowledge",
            "why": "Alley = local knowledge, shortcuts. Feels grassroots."
        },
        {
            "name": "ScriptSage",
            "username": "scriptsage",
            "email": "scriptsage@proton.me",
            "display": "Script Sage",
            "bio": "Wisdom from years in the trenches 🧙 | Daily code insights",
            "vibe": "Experienced, mentor-like, human wisdom",
            "why": "Sage = wise person. Implies human experience."
        },
        {
            "name": "ByteBistro",
            "username": "bytebistro",
            "email": "bytebistro@proton.me",
            "display": "Byte Bistro",
            "bio": "Serving up daily code recipes 🍽️ | Small portions, big flavor",
            "vibe": "Culinary metaphor, bite-sized content",
            "why": "Bistro = small, quality-focused. Implies curation."
        },
        {
            "name": "CodeCabin",
            "username": "codecabin",
            "email": "codecabin@proton.me",
            "display": "Code Cabin",
            "bio": "Cozy coding corner in the woods 🏕️ | Daily campfire wisdom",
            "vibe": "Cozy, personal, intimate",
            "why": "Cabin = personal space. Feels authentic and small-scale."
        },
        {
            "name": "DevDrift",
            "username": "devdrift",
            "email": "devdrift@proton.me",
            "display": "Dev Drift",
            "bio": "Thoughts while coding late at night 🌙 | Daily musings",
            "vibe": "Introspective, personal blog feel",
            "why": "Drift = wandering thoughts. Very human."
        },
        {
            "name": "StackStories",
            "username": "stackstories",
            "email": "stackstories@proton.me",
            "display": "Stack Stories",
            "bio": "Real tales from the tech stack 📚 | Learning through storytelling",
            "vibe": "Narrative, story-driven, human experience",
            "why": "Stories = human element. Implies personal experience."
        }
    ]
    
    return brands

def print_recommendations():
    brands = generate_human_brands()
    
    print("🎨 HUMAN-FIRST BRAND OPTIONS")
    print("=" * 70)
    print("\nThese avoid AI slop tripwires by sounding INTENTIONAL and HUMAN.\n")
    
    for i, brand in enumerate(brands, 1):
        print(f"\n{i}. {brand['name']} (@{brand['username']})")
        print(f"   Email: {brand['email']}")
        print(f"   Bio: {brand['bio']}")
        print(f"   Vibe: {brand['vibe']}")
        print(f"   Why It Works: {brand['why']}")
        print(f"   {'-' * 66}")
    
    print("\n" + "=" * 70)
    print("ANTI-AI-SLOP STRATEGY:")
    print("=" * 70)
    print("""
1. NO NUMBERS in username (screams bot)
2. Metaphor-based names (kitchen, forge, cabin = human places)
3. Alliteration (pixel pioneer, script sage = deliberate wordplay)
4. Cultural references (coffee, cooking = human activities)
5. Emotional words (cozy, wisdom, discovery = human feelings)

CONTENT STRATEGY TO AVOID DETECTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Add humor/sarcasm in captions ("This works... usually 😅")
✓ Include personal anecdotes ("Spent 3 hours debugging this...")
✓ Vary posting times (not rigid schedule)
✓ Mix AI videos with human commentary
✓ Use natural language errors occasionally ("gonna" not "going to")
✓ Respond to comments personally
✓ Share failures, not just wins
✓ Reference current events/memes
✓ Use emojis naturally (not perfectly)
✓ Post "behind the scenes" content

UPLOAD CADENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TikTok: 2-3/day (6am, 2pm, 8pm) - stagger by 15-30 min
YouTube Shorts: 1-2/day (12pm, 6pm) - not exact time
Twitter: 3-5/day - natural rhythm, not scheduled
Reddit: 1/day max - different subreddits

HUMANIZATION CHECKLIST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Profile pic: Simple logo (NOT generic AI art)
□ Banner: Screenshot of actual code or workspace
□ Bio: First person ("I share...") not third ("Daily tips...")
□ First posts: Introduce yourself (even if fake persona)
□ Engage with others before posting
□ Use platform-specific slang (TikTok: "fy" Reddit: "TIL")
□ Make typos occasionally (then correct with *)
□ Use thread replies on Twitter (not just standalone)
□ Share other people's content too (not 100% self-promotion)
    """)
    
    print("\n" + "=" * 70)
    print("RECOMMENDED PICK: DevKitchen or CodeBrews")
    print("=" * 70)
    print("""
Both have:
- Strong metaphor (cooking/coffee = human activity)
- No numbers
- Easy to remember
- Room for personality
- Natural content angles (recipes, brewing process)

DevKitchen = "Cooking up a tutorial on..."
CodeBrews = "Fresh brew: Python list comprehensions"
    """)

if __name__ == "__main__":
    print_recommendations()
