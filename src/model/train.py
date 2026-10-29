# src/model/train.py
import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification, Trainer, TrainingArguments
from datasets import Dataset

MODEL_NAME = "google-bert/bert-base-uncased"
LABEL2ID = {
    "O": 0,
    "B-CARD": 1, "I-CARD": 2,
    "B-PHONE": 3, "I-PHONE": 4,
    "B-PAN": 5, "I-PAN": 6,
    "B-EMAIL": 7, "I-EMAIL": 8,
    "B-IP": 9, "I-IP": 10,
    "B-URL": 11, "I-URL": 12,
    "B-OTP": 13, "I-OTP": 14,
    "B-PERSON": 15, "I-PERSON": 16,
    "B-ENTITY": 17, "I-ENTITY": 18,
}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
NUM_LABELS = len(LABEL2ID)

def load_corpus(path):
    texts, labels = [], []
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            texts.append(rec["text"])
            # Convert string labels to integer IDs
            labels.append([LABEL2ID[l] for l in rec["labels"]])
    return texts, labels

def tokenize(inputs, tokenizer, max_length=128):
    return tokenizer(
        inputs["text"],
        padding="max_length",
        truncation=True,
        max_length=max_length,
        is_split_into_words=False,
    )

class PIIDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.encodings = tokenizer(texts, truncation=True, padding=True, max_length=max_length)
        self.labels = labels
        self.encodings = self.encodings

    def __len__(self):
        return len(self.encodings["input_ids"])

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item

def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    # Simplified: return accuracy (expand for full seq-tag metrics)
    correct = (preds == labels).sum()
    total = len(labels)
    return {"accuracy": correct / total}

def tokenize_and_align_labels(texts, labels, tokenizer, max_length=128):
    """Tokenize text and align character-level B-/I- labels to subword tokens."""
    tokenized = tokenizer(texts, truncation=True, padding="max_length", max_length=max_length, return_offsets_mapping=True)
    
    aligned_labels = []
    for i, label in enumerate(labels):
        offsets = tokenized["offset_mapping"][i]
        label_ids = []
        for start, end in offsets:
            if start == 0 and end == 0:
                label_ids.append(-100)
            else:
                # Use label from first character of this token
                char_label = label[start]
                if isinstance(char_label, str):
                    char_label = LABEL2ID[char_label]
                label_ids.append(char_label)
        aligned_labels.append(label_ids)
    
    tokenized.pop("offset_mapping")
    tokenized["labels"] = aligned_labels
    return tokenized

def main():
    tokenizer = AutoTokenizer.from_pretrained("models/google-bert_bert-base-uncased")
    model = AutoModelForTokenClassification.from_pretrained(
        "models/google-bert_bert-base-uncased",
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    texts, labels = load_corpus("data/corpus/train.jsonl")
    
    # Split into train/val (90/10)
    split = int(0.9 * len(texts))
    train_texts, val_texts = texts[:split], texts[split:]
    train_labels, val_labels = labels[:split], labels[split:]
    
    # Build datasets
    train_encodings = tokenize_and_align_labels(train_texts, train_labels, tokenizer)
    val_encodings = tokenize_and_align_labels(val_texts, val_labels, tokenizer)
    train_dataset = Dataset.from_dict(train_encodings)
    val_dataset = Dataset.from_dict(val_encodings)

    training_args = TrainingArguments(
        output_dir="./models/pii_classifier",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        learning_rate=2e-5,
        logging_steps=50,
        save_steps=500,
        eval_strategy="steps",
        eval_steps=250,
        max_steps=2000,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model("./models/pii_classifier")
    print("Saved model to ./models/pii_classifier")

if __name__ == "__main__":
    main()
