import sys

from augmentation import augmentation
from generation import generation
from retrieval import retrieval

# question = sys.argv[1]
# question = "What is the capital of France?"
question = "Who is CEO ?"

relevant_chunks = retrieval(question)
prompts = augmentation(question, relevant_chunks)
answer = generation(prompts)

print('***** Answer from LLM *****')
print(answer)

if 'I could not find an answer to your question.' not in answer:

    print('For more details, please refer to the following documents:')
    for chunk in relevant_chunks:
        print(chunk['document'])