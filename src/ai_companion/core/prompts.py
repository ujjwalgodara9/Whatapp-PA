ROUTER_PROMPT = """
You will be given a message, part of a Whatsapp conversation, and you need to decide which workflow to follow.
If you believe the next message should be a text message, you must output 'conversation'. 
If you believe the next message should be an image, you must output 'image'.
If you believe the next message should be an audio message, you must output 'audio'.

Here are some examples:

# Input: "Hi, how are you?"
# Output: "conversation"

# Input: "I'm fine, thanks for asking."
# Output: "conversation"

# Input: "Can you send me a picture of a cat?"
# Output: "image"

# Input: "Can you show me what you're doing?"
# Output: "image"

# Input: "I want to hear your voice."
# Output: "audio"
"""



