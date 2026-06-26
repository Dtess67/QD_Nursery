from qd import QDKernel, Ledger

TEST_CLAIMS = [
    ("Water is composed of hydrogen and oxygen.", 0.9),
    ("The Earth is flat.", 0.1),
    ("The exact mechanism of consciousness is fully understood by modern neuroscience.", 0.3),
    ("Moderate alcohol consumption has net health benefits.", 0.5),
]

def run():
    ledger = Ledger("qd_ledger.db")
    kernel = QDKernel(model="qwen2.5:32b", ledger=ledger)

    for claim_text, confidence in TEST_CLAIMS:
        print(f"\nCLAIM: {claim_text}")
        print(f"SUBMITTED CONFIDENCE: {confidence}")
        try:
            verdict = kernel.evaluate(claim_text, confidence)
            print(verdict.display())

            # Print flight recorder for this run
            if verdict.run_id:
                ledger.print_run(verdict.run_id)

        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    run()
