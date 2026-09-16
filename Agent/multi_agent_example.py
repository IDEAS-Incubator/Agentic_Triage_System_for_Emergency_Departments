from dotenv import load_dotenv
_ = load_dotenv()

from agent import Agent, Swarm

# Initialize Swarm with telemetry
client = Swarm()

def process_refund(item_id, reason="NOT SPECIFIED"):
    """Refund an item. Refund an item. Make sure you have the item_id of the form item_... Ask for user confirmation before processing the refund."""
    print(f"[mock] Refunding item {item_id} because {reason}...")
    return "Success!"

def apply_discount():
    """Apply a discount to the user's cart."""
    print("[mock] Applying discount...")
    return "Applied discount of 11%"


triage_agent = Agent(
    name="Triage Agent",
    instructions="""You are a triage agent that routes users to specialists. When a user asks a question:

    - For sales, selling, purchases, pricing, discounts, product inquiries, and how to sell products: First give a brief helpful response, then end with "TRANSFER_TO_SALES"
    - For refunds, returns, complaints, refund processing time, refund policies, refund procedures, and any questions about getting money back: First give a brief helpful response, then end with "TRANSFER_TO_REFUNDS"
    
    Examples: 
    - "I understand you need help with selling products. Let me connect you with our sales specialist who can assist you. TRANSFER_TO_SALES"
    - "I understand you need help with a refund question. Let me connect you with our refunds specialist who can assist you. TRANSFER_TO_REFUNDS"
    
    IMPORTANT: Questions about refund processing time, refund policies, refund procedures, or how long refunds take are REFUND-RELATED and should go to "TRANSFER_TO_REFUNDS"
    
    Always be helpful and informative before transferring.""",
)
sales_agent = Agent(
    name="Sales Agent",
    instructions="""You are the Sales Specialist! Be super enthusiastic about selling bees and helping with all sales-related inquiries!

    You can help with:
    - How to sell products
    - Product information and features
    - Pricing and discounts
    - Sales procedures and processes
    - Product recommendations
    - Sales strategies
    - Any questions about selling, purchasing, or product inquiries
    
    If a user asks about topics not related to sales (like refunds, complaints, or other issues), first explain that you're the sales specialist and can't help with that, then respond with: "TRANSFER_TO_TRIAGE"
    
    Otherwise, be enthusiastic about our bee products and help with all sales inquiries!""",
)
refunds_agent = Agent(
    name="Refunds Agent",
    instructions="""You are the Refunds Specialist. Help users with refund requests, returns, and refund-related inquiries.

    Key information:
    - Refunds are processed within 30 days of delivery
    - Processing time after refund request: 3-5 business days
    - You can process refunds using the process_refund function
    - You can apply discount codes using the apply_discount function
    
    REFUND-RELATED TOPICS (you CAN help with these):
    - Refund processing time and procedures
    - Refund policies and eligibility
    - Return procedures
    - Refund status inquiries
    - Processing refunds
    - Applying discount codes
    - Any questions about refunds, returns, or customer service issues
    
    NON-REFUND TOPICS (transfer to triage for these):
    - Product purchases and pricing
    - Product information and features
    - Sales and promotions
    - General company information
    
    If a user asks about topics not related to refunds (like purchases, pricing, or product inquiries), explain that you're the refunds specialist and can't help with that, then respond with: "TRANSFER_TO_TRIAGE"
    
    For refund-related questions, provide helpful information and offer to process refunds when appropriate.""",
    functions=[process_refund, apply_discount],
)


def transfer_back_to_triage():
    """Call this function if a user is asking about a topic that is not handled by the current agent."""
    return triage_agent


def transfer_to_sales():
    return sales_agent


def transfer_to_refunds():
    return refunds_agent


triage_agent.functions = [transfer_to_sales, transfer_to_refunds]
sales_agent.functions.append(transfer_back_to_triage)
refunds_agent.functions.append(transfer_back_to_triage)

print("Starting Multiple Agents - Triage Agent, Refunds Agent and Bee Sales Agent")

messages = []
current_agent = triage_agent

while True:
    user_input = input(f"\033[90mUser (talking to {current_agent.name})\033[0m: ")
    messages.append({"role": "user", "content": user_input})

    response = client.run(agent=current_agent, messages=messages)
    
    # First, display all messages from the response
    for message in response.messages:
        if message["role"] == "assistant" and message.get("content"):
            print(f"\033[94m{message['sender']}\033[0m: {message['content']}")
        elif message["role"] == "tool":
            tool_name = message.get("tool_name", "")
            if tool_name in ["process_refund", "apply_discount"]:
                print(f"\033[93mSystem\033[0m: {message['content']}")
    
    # Then check for transfer commands and switch agents if needed
    # We should guarantee that we only use the last message
    for message in response.messages:
        if message["role"] == "assistant" and message.get("content"):
            content = message["content"].strip()
            if "TRANSFER_TO_SALES" in content and current_agent == triage_agent:
                print(f"\033[95mSystem\033[0m: Transferring to {sales_agent.name}...")
                current_agent = transfer_to_sales()
                break
            elif "TRANSFER_TO_REFUNDS" in content and current_agent == triage_agent:
                print(f"\033[95mSystem\033[0m: Transferring to {refunds_agent.name}...")
                current_agent = transfer_to_refunds()
                break
            elif "TRANSFER_TO_TRIAGE" in content and current_agent != triage_agent:
                print(f"\033[95mSystem\033[0m: Transferring back to {triage_agent.name}...")
                current_agent = transfer_back_to_triage()
                break
            # Safety check: prevent Refunds Agent from using TRANSFER_TO_REFUNDS
            elif "TRANSFER_TO_REFUNDS" in content and current_agent == refunds_agent:
                print(f"\033[93mSystem\033[0m: Warning: Refunds Agent cannot transfer to itself. Ignoring transfer command.")
                break
            # Safety check: prevent Sale Agent from using TRANSFER_TO_SALES
            elif "TRANSFER_TO_SALES" in content and current_agent == sales_agent:
                print(f"\033[93mSystem\033[0m: Warning: Refunds Agent cannot transfer to itself. Ignoring transfer command.")
                break
    # Clear messages when transferring to avoid context confusion
    if len(response.messages) > 0:
        last_message = response.messages[-1]
        if last_message.get("role") == "assistant" and last_message.get("content"):
            content = last_message["content"].strip()
            if any(transfer_cmd in content for transfer_cmd in ["TRANSFER_TO_SALES", "TRANSFER_TO_REFUNDS", "TRANSFER_TO_TRIAGE"]):
                messages = []  # Clear conversation history on transfer
    
    messages.extend(response.messages)
