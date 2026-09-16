from dotenv import load_dotenv
_ = load_dotenv()

import json
from agent import pretty_print_messages, Agent, Swarm


def get_weather(location, time="now"):
    # need to implement the weather API calls
    return json.dumps({"location": location, "temperature": "65", "time": time})


def send_email(recipient, subject, body):
    # need code to implement gmail API calls
    return f"Sent! email to {recipient} with the subject: {subject} and body: {body}"


agent = Agent(
    name="Assistant Agent",
    model = "llama3.2",
    instructions="""You are a helpful agent for giving information on weather and sending emails. 

                    IMPORTANT FUNCTION CALLING RULES:
                    1. WEATHER: When a user asks about weather (e.g., "how is the weather in [location]", "what's the temperature in [city]", "weather in [place]", etc.), you MUST call the get_weather function with the location parameter.

                    2. EMAIL: When a user wants to send an email (e.g., "send email to [recipient]", "email [person]", "send email", etc.), you MUST call the send_email function. If the user doesn't provide subject or body, ask for them but still call the function with placeholder values.

                    3. OTHER QUERIES: For any other questions NOT about weather or sending emails, respond using your own knowledge without calling any functions.

                    EXAMPLES:
                    - "send email to john@example.com" → Call send_email function
                    - "how is the weather in Paris" → Call get_weather function  
                    - "what is machine learning" → Use your own knowledge (no function call)

                    Always be helpful and provide clear, informative responses.""",
    functions=[get_weather, send_email],
)

client = Swarm()

print("Starting Single Agent - Assistant Agent")
print('I can help with weather, send emails, or answer general questions. What would you like to know?')
print('Type "quit" or "exit" to end the program.')

memory = []

while True:
    user_input = input("User:")
    memory.append({"role": "user", "content": user_input})
    
    # Check for quit command
    if user_input.lower() in ["quit", "exit"]:
        print("Exiting the program. Goodbye")
        break
    
    response = client.run(agent=agent, messages=memory)
    
    pretty_print_messages(response.messages)

    memory.extend(response.messages)

    agent = response.agent