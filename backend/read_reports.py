
import sys

files = ["output_test_1.txt", "output_test_2.txt"]

for fname in files:
    print(f"\n--- {fname} ---")
    try:
        # Try utf-16 first as powershell > creates utf-16
        content = open(fname, "r", encoding="utf-16", errors="ignore").read()
    except:
        content = open(fname, "r", encoding="utf-8", errors="ignore").read()
        
    lines = content.splitlines()
    for line in lines:
        if "TAHMİN" in line or "GÜVEN" in line or "Tespit Edilen" in line:
            print(line)
        if "Happy" in line or "Fear" in line or "Sad" in line or "Angry" in line:
            # Print context if it looks like a probability line
            if "%" in line: 
                print(line)
