"""
ADAPT Research — Experiment 1: Bloom Taxonomy Cognitive Classification Comparison

Compares:
1. Baseline Keyword/Rule Classifier
2. LLM Zero-shot / Few-shot Cognitive Classifier
Evaluates: Accuracy, Precision, Recall, Macro-F1, Cohen's Kappa.
"""

import asyncio
from typing import Dict, List
from sklearn.metrics import accuracy_score, classification_report, cohen_kappa_score

# Labeled benchmark test set for NLP & Computer Science questions
TEST_BENCHMARK = [
    {"text": "Define tokenization and explain why whitespace splitting is insufficient.", "true_level": "Understand"},
    {"text": "State Bayes' theorem and list its fundamental assumptions.", "true_level": "Remember"},
    {"text": "Calculate the perplexity of a bigram language model on a 50-word test corpus.", "true_level": "Apply"},
    {"text": "Implement the Viterbi decoding algorithm in Python for HMM part-of-speech tagging.", "true_level": "Apply"},
    {"text": "Compare and contrast Skip-gram and Continuous Bag of Words (CBOW) Word2Vec architectures.", "true_level": "Analyze"},
    {"text": "Deconstruct the multi-head attention mechanism and analyze its computational bottleneck for sequence length N.", "true_level": "Analyze"},
    {"text": "Critique the use of BLEU score versus ROUGE for evaluating abstractive summarization models.", "true_level": "Evaluate"},
    {"text": "Assess the ethical and security vulnerabilities in training large language models on uncurated web scrapes.", "true_level": "Evaluate"},
    {"text": "Design a hybrid neuro-symbolic question answering architecture for biomedical clinical records.", "true_level": "Create"},
    {"text": "Formulate a novel loss function combining contrastive loss and cross-entropy for low-resource translation.", "true_level": "Create"},
    {"text": "List the six levels of Bloom's Revised Taxonomy in ascending order.", "true_level": "Remember"},
    {"text": "Explain the difference between stemming and lemmatization with illustrative examples.", "true_level": "Understand"},
]


async def run_bloom_experiment():
    from app.ai.bloom_classifier import KeywordBloomClassifier, LLMBloomClassifier

    print("===============================================================")
    print(" ADAPT Research — Bloom Cognitive Level Classification Experiment")
    print("===============================================================\n")

    keyword_clf = KeywordBloomClassifier()
    llm_clf = LLMBloomClassifier()

    y_true = [item["true_level"] for item in TEST_BENCHMARK]
    y_pred_keyword = []
    y_pred_llm = []

    print(f"Evaluating on {len(TEST_BENCHMARK)} labeled benchmark questions...\n")

    for item in TEST_BENCHMARK:
        kw_res = await keyword_clf.classify(item["text"])
        llm_res = await llm_clf.classify(item["text"])

        y_pred_keyword.append(kw_res.level)
        y_pred_llm.append(llm_res.level)

    # Metrics
    kw_acc = accuracy_score(y_true, y_pred_keyword)
    llm_acc = accuracy_score(y_true, y_pred_llm)
    kappa = cohen_kappa_score(y_true, y_pred_llm)

    print("--- MODEL COMPARISON RESULTS ---")
    print(f"1. Keyword Baseline Classifier Accuracy: {kw_acc * 100:.1f}%")
    print(f"2. LLM Cognitive Classifier Accuracy:   {llm_acc * 100:.1f}%")
    print(f"3. Cohen's Kappa Inter-Annotator Agreement: {kappa:.3f}\n")

    print("--- LLM CLASSIFICATION REPORT ---")
    print(classification_report(y_true, y_pred_llm, zero_division=0))


if __name__ == "__main__":
    asyncio.run(run_bloom_experiment())
