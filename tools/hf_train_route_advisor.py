# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "datasets>=3.5.0",
#   "transformers>=4.49.0",
#   "accelerate>=1.6.0",
#   "evaluate>=0.4.3",
#   "numpy>=2.1.0",
# ]
# ///

from __future__ import annotations

from pathlib import Path

import evaluate
import numpy as np
from datasets import ClassLabel, load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "hf" / "route_advisor_train.jsonl"
OUTPUT_DIR = ROOT / "artifacts" / "hf_route_advisor"
MODEL_ID = "distilbert/distilbert-base-uncased"


def main() -> None:
    dataset = load_dataset("json", data_files=str(DATA_FILE), split="train")
    labels = sorted(set(dataset["label"]))
    label_feature = ClassLabel(names=labels)
    dataset = dataset.map(lambda row: {"label": label_feature.str2int(row["label"])})
    dataset = dataset.train_test_split(test_size=0.2, seed=42)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    def tokenize(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        return tokenizer(batch["text"], truncation=True)

    tokenized = dataset.map(tokenize, batched=True)
    metric = evaluate.load("accuracy")

    def compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
        logits, labels_np = eval_pred
        preds = np.argmax(logits, axis=-1)
        return metric.compute(predictions=preds, references=labels_np)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        num_labels=len(labels),
        id2label={idx: name for idx, name in enumerate(labels)},
        label2id={name: idx for idx, name in enumerate(labels)},
    )
    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=12,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        logging_steps=5,
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"saved route advisor model to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
