"""
Validation script for LLM setup and package imports
"""
def validate_package_imports():
    """Validate that all required packages can be imported"""
    print("=== Package Import Validation ===")
    packages_to_test = [
        ("openai", "OpenAI API client"),
        ("transformers", "HuggingFace Transformers"),
        ("torch", "PyTorch"),
        ("sentence_transformers", "Sentence Transformers"),
        ("dotenv", "Python dotenv")
    ]
    import_results = {}
    for package_name, description in packages_to_test:
        try:
            __import__(package_name)
            print(f"✓ {package_name}: {description} - OK")
            import_results[package_name] = True
        except ImportError as e:
            print(f"✗ {package_name}: {description} - FAILED: {str(e)}")
            import_results[package_name] = False
    return import_results
def test_openai_mock():
    """Test OpenAI client creation (without API call)"""
    print("\n=== OpenAI Client Test ===")
    try:
        import openai
        # Test client creation with dummy key
        client = openai.OpenAI(api_key="test_key")
        print("✓ OpenAI client creation successful")
        return True
    except Exception as e:
        print(f"✗ OpenAI client creation failed: {str(e)}")
        return False
def test_transformers_basic():
    """Test basic transformers functionality"""
    print("\n=== Transformers Basic Test ===")
    try:
        from transformers import AutoTokenizer
        # Test tokenizer loading (this should work without GPU)
        tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
        # Test basic tokenization
        test_text = "Hello, this is a test."
        tokens = tokenizer.encode(test_text)
        decoded = tokenizer.decode(tokens)
        print(f"✓ Tokenizer test successful")
        print(f"  Original: {test_text}")
        print(f"  Tokens: {tokens}")
        print(f"  Decoded: {decoded}")
        return True
    except Exception as e:
        print(f"✗ Transformers test failed: {str(e)}")
        return False
def test_torch_setup():
    """Test PyTorch setup and device detection"""
    print("\n=== PyTorch Setup Test ===")
    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")
        print(f"✓ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✓ CUDA device count: {torch.cuda.device_count()}")
            print(f"✓ Current device: {torch.cuda.current_device()}")
        else:
            print("ℹ Running on CPU (no CUDA available)")
        # Test basic tensor operations
        x = torch.randn(2, 3)
        y = torch.randn(3, 2)
        z = torch.mm(x, y)
        print(f"✓ Basic tensor operations working")
        return True
    except Exception as e:
        print(f"✗ PyTorch test failed: {str(e)}")
        return False
def main():
    """Main validation function"""
    print("LLM Setup Validation Script")
    print("=" * 40)
    # Test package imports
    import_results = validate_package_imports()
    # Test individual components
    openai_ok = test_openai_mock()
    transformers_ok = test_transformers_basic()
    torch_ok = test_torch_setup()
    # Summary
    print("\n" + "=" * 40)
    print("VALIDATION SUMMARY:")
    print("=" * 40)
    all_imports_ok = all(import_results.values())
    all_tests_ok = openai_ok and transformers_ok and torch_ok
    print(f"Package Imports: {'✓ PASS' if all_imports_ok else '✗ FAIL'}")
    print(f"OpenAI Client: {'✓ PASS' if openai_ok else '✗ FAIL'}")
    print(f"Transformers: {'✓ PASS' if transformers_ok else '✗ FAIL'}")
    print(f"PyTorch: {'✓ PASS' if torch_ok else '✗ FAIL'}")
    overall_status = all_imports_ok and all_tests_ok
    print(f"\nOVERALL STATUS: {'✓ READY FOR LLM OPERATIONS' if overall_status else '✗ ISSUES NEED RESOLUTION'}")
    return overall_status
if __name__ == "__main__":
    main()