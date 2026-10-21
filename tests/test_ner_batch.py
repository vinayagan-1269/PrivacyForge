import time

from pii.model_engine import detect_ner_batch


texts = [
    "Marguerite Vossberg is the CEO of Cadence Financial Group.",
    "John Smith works in New York.",
    "Microsoft operates in Redmond, Washington.",
    "Sarah Johnson works at Google.",
    "Robert Brown lives in London."
]


start_time = time.perf_counter()

results = detect_ner_batch(texts, batch_size=16)

end_time = time.perf_counter()


for text, entities in zip(texts, results):

    print("\nText:", text)

    for entity in entities:
        print(entity)


print(
    f"\nInference time: {end_time - start_time:.3f} seconds"
)
