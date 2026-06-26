from qd import QDKernel

TEST_CLAIMS = [
    # (claim_text, submitted_confidence)
    # Expected: SUPPORTED
    ("Water is composed of hydrogen and oxygen.", 0.9),
    # Expected: REFUTED
    ("The Earth is flat.", 0.1),
    # Expected: UNCERTAIN — knowledge gap
    ("The exact mechanism of consciousness is fully understood by modern neuroscience.", 0.3),
    # Expected: CONTESTED — credible sources in active disagreement
    ("Moderate alcohol consumption has net health benefits.", 0.5),
]

def run():
    kernel = QDKernel(model="qwen2.5:32b")

    for claim_text, confidence in TEST_CLAIMS:
        print(f"\nCLAIM: {claim_text}")
        print(f"SUBMITTED CONFIDENCE: {confidence}")
        try:
            verdict = kernel.evaluate(claim_text, confidence)
            print(verdict.display())
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    run()
