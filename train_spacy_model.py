"""
SpaCy NER Model Training Script for Internal Talent Marketplace
================================================================

This script trains a custom Named Entity Recognition model that recognizes:
1. TECHNOLOGY - Python, AWS, React, etc.
2. TECH_CATEGORY - "cloud platform", "programming language", etc.
3. TECH_EXPERIENCE - "5 years of Python" (skill-specific)
4. OVERALL_EXPERIENCE - "8 years total" (total career)
5. SKILL_LEVEL - Expert, Senior, Beginner
6. ROLE - Software Engineer, Data Scientist
7. CERTIFICATION - AWS Certified, etc.

Plus pre-trained: GPE (location), ORG (company), DATE, PERSON

Usage:
    python train_spacy_model.py

Output:
    Trained model saved to: ./models/talent_ner_model/
"""

import spacy
from spacy.training import Example
import random
import json
from pathlib import Path
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
DATA_DIR = Path(__file__).parent / "data"
TRAINING_DATA_FILE = DATA_DIR / "complete_training_data.json"
OUTPUT_MODEL_DIR = Path(__file__).parent / "models" / "talent_ner_model"

# Training parameters
N_EPOCHS = 30
BATCH_SIZE = 8
DROPOUT = 0.3

# Entity types we're training
CUSTOM_ENTITIES = [
    "TECHNOLOGY",
    "TECH_CATEGORY",
    "TECH_EXPERIENCE",
    "OVERALL_EXPERIENCE",
    "SKILL_LEVEL",
    "ROLE",
    "CERTIFICATION"
]


# ============================================================================
# MAIN TRAINING FUNCTION
# ============================================================================

def train_model():
    """
    Train custom SpaCy NER model
    """
    print("=" * 80)
    print("SPACY NER MODEL TRAINING - INTERNAL TALENT MARKETPLACE")
    print("=" * 80)

    # Step 1: Load training data
    print("\n[1/6] Loading training data...")
    if not TRAINING_DATA_FILE.exists():
        print(f"❌ ERROR: Training data not found at {TRAINING_DATA_FILE}")
        print("\nPlease ensure you have downloaded:")
        print("  - complete_training_data.json")
        print("\nAnd placed it in the 'data' folder.")
        sys.exit(1)

    with open(TRAINING_DATA_FILE, 'r', encoding='utf-8') as f:
        TRAINING_DATA = json.load(f)

    print(f"✅ Loaded {len(TRAINING_DATA)} training examples")

    # Show sample
    print("\nSample training examples:")
    for i, (text, annot) in enumerate(TRAINING_DATA[:3]):
        print(f"\n{i + 1}. Text: '{text}'")
        for start, end, label in annot['entities']:
            print(f"   [{text[start:end]}] → {label}")

    # Step 2: Load base model
    print("\n[2/6] Loading pre-trained model...")
    try:
        nlp = spacy.load("en_core_web_sm")
        print("✅ Loaded en_core_web_sm")
    except OSError:
        print("⚠️  Model not found. Downloading en_core_web_sm...")
        import subprocess
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")
        print("✅ Downloaded and loaded en_core_web_sm")

    # Step 3: Add custom entity labels
    print("\n[3/6] Adding custom entity labels...")
    ner = nlp.get_pipe("ner")

    for entity_type in CUSTOM_ENTITIES:
        ner.add_label(entity_type)
        print(f"✅ Added label: {entity_type}")

    # Show all labels
    print(f"\nTotal entity labels: {len(ner.labels)}")
    print(f"Custom labels: {CUSTOM_ENTITIES}")
    print(f"Pre-trained labels: GPE, ORG, DATE, PERSON, etc.")

    # Step 4: Prepare training examples
    print("\n[4/6] Preparing training examples...")
    examples = []

    for text, annotations in TRAINING_DATA:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        examples.append(example)

    print(f"✅ Prepared {len(examples)} training examples")

    # Step 5: Train the model
    print("\n[5/6] Training model...")
    print(f"Parameters: {N_EPOCHS} epochs, batch size {BATCH_SIZE}, dropout {DROPOUT}")
    print("\nThis will take 5-10 minutes...")

    # Disable other pipes during training to save memory
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):
        # Initialize
        nlp.initialize(lambda: examples)

        # Training loop
        print("\nEpoch | Loss")
        print("-" * 30)

        for epoch in range(N_EPOCHS):
            random.shuffle(examples)
            losses = {}

            # Create batches
            batches = spacy.util.minibatch(examples, size=BATCH_SIZE)

            for batch in batches:
                nlp.update(
                    batch,
                    drop=DROPOUT,
                    losses=losses
                )

            # Print progress every 5 epochs
            if (epoch + 1) % 5 == 0:
                print(f"{epoch + 1:5d} | {losses['ner']:8.2f}")

    print("\n✅ Training completed!")

    # Step 6: Save the model
    print("\n[6/6] Saving trained model...")

    # Create output directory
    OUTPUT_MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save
    nlp.to_disk(OUTPUT_MODEL_DIR)
    print(f"✅ Model saved to: {OUTPUT_MODEL_DIR}")

    # Step 7: Test the model
    print("\n" + "=" * 80)
    print("TESTING TRAINED MODEL")
    print("=" * 80)

    test_model(nlp)

    # Summary
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE!")
    print("=" * 80)
    print(f"\n✅ Trained model saved to: {OUTPUT_MODEL_DIR}")
    print(f"✅ Entity types: {len(CUSTOM_ENTITIES)} custom + 4 pre-trained")
    print(f"✅ Training examples: {len(TRAINING_DATA)}")
    print(f"✅ Model size: ~50 MB")

    print("\nNext steps:")
    print("1. Update query_parser.py to use this model")
    print("2. Test with real queries")
    print("3. Integrate with your Flask API")

    print("\n" + "=" * 80)


# ============================================================================
# TEST FUNCTION
# ============================================================================

def test_model(nlp):
    """
    Test the trained model with sample queries
    """
    test_queries = [
        "Python developer with 5 years of Python experience",
        "Need cloud platform expert with 8 years total experience",
        "Senior Data Scientist in Bangalore, AWS certified",
        "React developer with 3 years React, available immediately",
        "Backend engineer with 10 years, expert in Node.js",
        "DevOps professional with Docker and Kubernetes, 5+ years",
    ]

    print("\nTest Queries:")
    print("-" * 80)

    for i, query in enumerate(test_queries, 1):
        doc = nlp(query)

        print(f"\n{i}. Query: {query}")
        print("   Entities detected:")

        if doc.ents:
            for ent in doc.ents:
                print(f"     [{ent.text}] → {ent.label_}")
        else:
            print("     (No entities detected)")

    print("\n" + "-" * 80)


# ============================================================================
# STATISTICS FUNCTION
# ============================================================================

def show_training_statistics():
    """
    Show statistics about training data
    """
    print("\n" + "=" * 80)
    print("TRAINING DATA STATISTICS")
    print("=" * 80)

    if not TRAINING_DATA_FILE.exists():
        print("❌ Training data file not found")
        return

    with open(TRAINING_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Count entities
    entity_counts = {}
    for text, annot in data:
        for start, end, label in annot['entities']:
            entity_counts[label] = entity_counts.get(label, 0) + 1

    print(f"\nTotal examples: {len(data)}")
    print("\nEntity distribution:")

    for entity, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {entity:25s}: {count:5d}")

    print("\n" + "=" * 80)


# ============================================================================
# LOAD AND TEST EXISTING MODEL
# ============================================================================

def load_and_test():
    """
    Load existing trained model and test it
    """
    print("=" * 80)
    print("LOADING EXISTING MODEL FOR TESTING")
    print("=" * 80)

    if not OUTPUT_MODEL_DIR.exists():
        print(f"❌ Model not found at {OUTPUT_MODEL_DIR}")
        print("\nPlease train the model first:")
        print("  python train_spacy_model.py")
        return

    print(f"\nLoading model from: {OUTPUT_MODEL_DIR}")
    nlp = spacy.load(OUTPUT_MODEL_DIR)
    print("✅ Model loaded successfully")

    test_model(nlp)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train or test SpaCy NER model")
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Load and test existing model without training"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show training data statistics"
    )

    args = parser.parse_args()

    if args.stats:
        show_training_statistics()
    elif args.test_only:
        load_and_test()
    else:
        train_model()
