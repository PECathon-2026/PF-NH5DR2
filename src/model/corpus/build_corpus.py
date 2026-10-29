# src/model/corpus/build_corpus.py
import json, random, re
from faker import Faker

fake = Faker('en_US')
random.seed(42)

LABEL_TYPES = ["CARD", "PHONE", "PAN", "EMAIL", "IP", "URL", "OTP", "PERSON", "ENTITY"]

def generate_phone():
    return f"{random.randint(1000000000,9999999999)}"

def generate_otp():
    return f"{random.randint(100000,999999)}"

def generate_card():
    # Luhn-valid test card
    return "4532015112830366"

def generate_email():
    return f"{fake.user_name()}@example.com"

def generate_pan():
    return f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{''.join(random.choices('1234567890', k=10))}"

def generate_ip():
    octets = [str(random.randint(1, 255)) for _ in range(4)]
    return ".".join(octets)

def generate_url():
    return f"https://example.com/path/{random.randint(1000,9999)}"

def generate_person():
    return f"{fake.first_name()} {fake.last_name()}"

def label_entities(text):
    """Simple labeler - expand later with model"""
    labels = ["O"] * len(text)
    # Replace card
    card = generate_card()
    if card in text:
        start = text.index(card)
        for i in range(len(card)):
            labels[start+i] = "B-CARD" if i==0 else "I-CARD"
    return labels

def build_record(text, labels):
    return {"text": text, "labels": labels}

# Build a small corpus
corpus = []
seed_texts = [
    f"My card number is {generate_card()} and my phone is {generate_phone()}",
    f"OTP for login is {generate_otp()} sent to {generate_phone()}",
    f"Hello {generate_person()}, contact me at {generate_email()}",
    f"IBAN: {generate_pan()}, IP: {generate_ip()}, URL: {generate_url()}",
    f"Device sent {generate_card()} and {generate_phone()} to server",
]
for t in seed_texts:
    corpus.append(build_record(t, label_entities(t)))

import os
os.makedirs("data/corpus", exist_ok=True)
with open("data/corpus/train.jsonl", "w") as f:
    for rec in corpus:
        f.write(json.dumps(rec) + "\n")
print(f"Wrote {len(corpus)} records to data/corpus/train.jsonl")
