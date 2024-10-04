from datasets import load_dataset

def load_gaia_dataset():
    return load_dataset("gaia-benchmark/GAIA")

def get_test_cases():
    dataset = load_gaia_dataset()
    return dataset['validation']