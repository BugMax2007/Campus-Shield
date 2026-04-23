# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "datasets>=3.5.0",
#   "transformers>=4.49.0",
#   "accelerate>=1.6.0",
#   "evaluate>=0.4.3",
#   "numpy>=2.1.0",
#   "sacrebleu>=2.5.0",
# ]
# ///

from __future__ import annotations

from pathlib import Path

import evaluate
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "hf" / "robot_coach_sft.jsonl"
OUTPUT_DIR = ROOT / "artifacts" / "hf_robot_coach"
MODEL_ID = "google/flan-t5-small"
PROMPT_PREFIX = "You are a campus safety guide. Give one short, concrete route coaching response.\n\n"


def main() -> None:
    dataset = load_dataset("json", data_files=str(DATA_FILE), split="train")
    dataset = dataset.train_test_split(test_size=0.25, seed=42)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    def preprocess(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        model_inputs = tokenizer(
            [PROMPT_PREFIX + item for item in batch["prompt"]],
            truncation=True,
            max_length=192,
        )
        labels = tokenizer(
            text_target=batch["response"],
            truncation=True,
            max_length=96,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized = dataset.map(preprocess, batched=True)
    metric = evaluate.load("sacrebleu")

    def compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
        preds, labels = eval_pred
        if isinstance(preds, tuple):
            preds = preds[0]
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        score = metric.compute(predictions=decoded_preds, references=[[item] for item in decoded_labels])
        return {"sacrebleu": score["score"]}

    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
    args = Seq2SeqTrainingArguments(
        output_dir=str(OUTPUT_DIR),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=3e-4,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        predict_with_generate=True,
        num_train_epochs=10,
        generation_max_length=96,
        logging_steps=5,
        report_to="none",
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model),
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"saved robot coach model to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
