# convert_kaggle_dialogs.py
import os
import json

# INPUT: The file you downloaded
INPUT_FILE = os.path.join("data", "dialogs.txt")

# OUTPUT: The file Arjun can use for training
OUTPUT_FILE = os.path.join("data", "arjun_training_data.jsonl")

def convert_dialogs():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find {INPUT_FILE}. Please download it first.")
        return

    count = 0
    skipped = 0

    print(f"Reading from {INPUT_FILE}...")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
        
        for line in fin:
            line = line.strip()
            if not line:
                continue
            
            # The dataset is usually "Question \t Answer"
            parts = line.split("\t")
            
            if len(parts) < 2:
                skipped += 1
                continue
            
            user_text = parts[0].strip()
            assist_text = parts[1].strip()
            
            # Create the chat structure Arjun expects
            entry = {
                "messages": [
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": assist_text}
                ]
            }
            
            # Write line to JSONL
            fout.write(json.dumps(entry) + "\n")
            count += 1

    print("------------------------------------------------")
    print(f"Conversion Complete!")
    print(f"Successfully converted: {count} dialogues")
    print(f"Skipped (bad format):   {skipped}")
    print(f"Saved to:               {OUTPUT_FILE}")
    print("------------------------------------------------")

if __name__ == "__main__":
    convert_dialogs()