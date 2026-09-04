import sys

from augmentation import augmentation
from generation import generation
from retrieval import retrieval

chat_history = []  # Collect chat history here (a sequence of messages)

def rag_app():
    print("Start chatting with the AI! Type 'exit' to end the conversation.")
    
    while True:
        print("\n type 'exit' to end the conversation.  ")
        # print("=" * 40)
        query = input("\n You:")
        if query.lower() == "exit":
            break
        # Process the user's query through the retrieval chain
        relevant_chunks = retrieval(query)
        prompts = augmentation(query, relevant_chunks)
        answer = generation(prompts)

        print('******* Answer from RAG *******')
        print(answer)


# Main function to start the continual chat
if __name__ == "__main__":
    rag_app()

