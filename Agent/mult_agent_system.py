from dotenv import load_dotenv
_ = load_dotenv()

from agent import Agent, Swarm

# Initialize Swarm with telemetry
client = Swarm()

# Intake Agent — 
intake_agent = Agent(
    name="Intake Agent",
    instructions="""You are an intake agent responsible for processing incoming patient information. When a user asks a question:
                    Ingest & normalize incoming HL7/FHIR events for the arriving patient; assemble the demographic and presenting-complaint snapshot.
                """,
    )

history_retrieval_agent = Agent(
    name="Patient History & Retrieval Agent",
    instructions="""You are a patient history and retrieval agent responsible for gathering and organizing a patient's medical history. When a user asks a question:
                    Retrieve relevant historical medical records, previous diagnoses, and treatment plans for the patient; ensure the information is accurate and up-to-date.
                """,
    )   

risk_rules_agent = Agent(
    name="Risk Rules Agent",
    instructions="""You are a risk-rules agent responsible for evaluating patient risk based on predefined rules and criteria. When a user asks a question:
                    Assess the patient's risk factors, apply relevant clinical rules, and provide recommendations for further action.
                """,
    )

triage_reasoning_agent = Agent(
    name="Triage Reasoning Agent",
    instructions="""You are a triage reasoning agent responsible for determining the urgency and priority of patient cases based on available information. When a user asks a question:
                    Analyze the patient's presenting complaints, medical history, and risk factors; provide a triage recommendation indicating the level of urgency and appropriate next steps.
                """,
    )   

critic_verification_agent = Agent(
    name="Critic / Verification Agent",
    instructions="""You are a critic and verification agent responsible for reviewing and validating the outputs of other agents. When a user asks a question:
                    Critically assess the recommendations and decisions made by other agents; ensure accuracy, consistency, and adherence to established rules and guidelines.
                """,
    )

# Presentation & Audit Agent
presentation_audit_agent = Agent(
    name="Presentation & Audit Agent",
    instructions="""You are a presentation and audit agent responsible for presenting patient information and auditing the actions of other agents. When a user asks a question:
                    Compile and present the patient's information in a clear and organized manner; review the actions and decisions of other agents to ensure compliance with established protocols and accuracy.
                """,
    )

