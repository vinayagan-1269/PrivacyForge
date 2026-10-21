from extractors.extractor import extract_file


file_path = r"D:\studies PDF\optiv project\case study\Case Study 2 Supporting Material\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
result = extract_file(file_path)

print("Number of extracted items:", len(result))

for item in result:
    print(item)
