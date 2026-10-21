from pii.regex_engine import detect_regex_pii


text = """
Marguerite Vossberg can be contacted at
m.vossberg@cadencefg.example.

Her phone number is +1 (555) 0114.
Employee ID: EMP-10234.

Server IP: 192.168.1.10.
"""


results = detect_regex_pii(text)

for result in results:
    print(result)
