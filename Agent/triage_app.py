from dotenv import load_dotenv
_ = load_dotenv()

from mult_agent_system import intake_agent, history_retrieval_agent, risk_rules_agent ,triage_reasoning_agent, critic_verification_agent,presentation_audit_agent

print("Starting Triage System")

# Initialize 
global_memory = []
current_agent = intake_agent

def triage_anaysis_simulation():
    print("Running triage analysis simulation...")
    while True:
        user_input = input(f"\033[90mUser (talking to {current_agent.name})\033[0m: ")
        global_memory.append({"role": "user", "content": user_input})

        response = current_agent.run(agent=current_agent, messages=global_memory)

        # First, display all messages from the response
        for message in response.messages:
            if message["role"] == "assistant" and message.get("content"):
                print(f"\033[94m{message['sender']}\033[0m: {message['content']}")
            elif message["role"] == "tool":
                tool_name = message.get("tool_name", "")
                if tool_name in ["process_refund", "apply_discount"]:
                    print(f"\033[93mSystem\033[0m: {message['content']}")
            
            
        global_memory.extend(response.messages)
    # return

if __name__ == "__main__":
    triage_anaysis_simulation()