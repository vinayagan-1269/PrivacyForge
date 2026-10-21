from pii.model_engine import detect_ner_pii


text = """
Marguerite Vossberg is the CEO of Cadence Financial Group.
She works in New York and manages the company's operations.
"""


results = detect_ner_pii(text)

for result in results:
    print(result)
