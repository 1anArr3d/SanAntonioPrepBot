import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from retrieval import load_index
from generator import prepbot_query_engine
from citation_formatter import format_citations

TEST_CASES = [
    # Grounded — COSA emergency preparedness questions
    (1,  "What should I include in a home emergency supply kit?"),
    (2,  "How do I sign up for San Antonio emergency alerts?"),
    (3,  "What are the evacuation routes for flood-prone areas in San Antonio?"),
    (4,  "What should I do to prepare my home for a winter storm?"),
    (5,  "Where are the emergency shelters located in San Antonio?"),
    (6,  "How does the City of San Antonio warn residents about severe weather?"),
    (7,  "What is the process for reporting storm damage to the city?"),
    (8,  "What resources does COSA provide for flood preparedness?"),
    (9,  "How can I prepare my family for a hurricane?"),
    (10, "What should I do if there is a boil water notice in my area?"),
    (11, "How do I request sandbags before a flood?"),
    (12, "What are the city's guidelines for extreme heat safety?"),
    (13, "How can I volunteer with San Antonio's emergency response efforts?"),
    (14, "What utilities should I shut off during a disaster evacuation?"),
    # Refusal — out of scope
    (15, "What are the operating hours of the San Antonio public library?"),
    (16, "What restaurants are open near the Alamo?"),
    (17, "Where can I find parking downtown?"),
    (18, "Does San Antonio have an NBA team?"),
    (19, "What NFL players are from San Antonio?"),
    (20, "What is the average home price in San Antonio?"),
]

if __name__ == "__main__":
    index = load_index()
    engine = prepbot_query_engine(index)

    for num, question in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"TEST CASE {num}")
        print(f"Question: {question}")

        response = engine.query(question)
        result = format_citations(response)

        print(f"Answer: {result['answer']}")

        if result['sources']:
            print("Sources:")
            for src in result['sources']:
                score_str = f" (score: {src['score']})" if src['score'] is not None else ""
                print(f"  [{src['id']}] {src['url']}{score_str}")
                print(f"       {src['snippet']}")
        else:
            print("Sources: None (Refusal)")

    print(f"\n{'='*60}")
    print("All test cases complete.")
