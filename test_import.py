# Test script to validate all imports work correctly
import sys

print("="*70)
print("🧪 Testing batch_cal_volume.py imports...")
print("="*70)

try:
    # Test 1: Import the new class
    print("\n1️⃣ Testing: from batch_cal_volume import LatticeParameterCalculator")
    from batch_cal_volume import LatticeParameterCalculator
    print("   ✅ SUCCESS: LatticeParameterCalculator imported")
    
    # Test 2: Import the backward compatibility alias
    print("\n2️⃣ Testing: from batch_cal_volume import XRayDiffractionAnalyzer")
    from batch_cal_volume import XRayDiffractionAnalyzer
    print("   ✅ SUCCESS: XRayDiffractionAnalyzer imported")
    
    # Test 3: Verify they are the same class
    print("\n3️⃣ Testing: XRayDiffractionAnalyzer is LatticeParameterCalculator")
    if XRayDiffractionAnalyzer is LatticeParameterCalculator:
        print("   ✅ SUCCESS: Alias points to correct class")
    else:
        print("   ❌ FAIL: Alias mismatch")
        sys.exit(1)
    
    # Test 4: Check key methods exist
    print("\n4️⃣ Testing: Key methods exist")
    required_methods = ['__init__', 'calculate', 'analyze', 'read_peak_data', 
                       'fit_lattice_parameters', 'save_results_to_csv']
    for method in required_methods:
        if hasattr(LatticeParameterCalculator, method):
            print(f"   ✅ Method found: {method}")
        else:
            print(f"   ❌ Method missing: {method}")
            sys.exit(1)
    
    # Test 5: Check CRYSTAL_SYSTEMS
    print("\n5️⃣ Testing: CRYSTAL_SYSTEMS attribute exists")
    if hasattr(LatticeParameterCalculator, 'CRYSTAL_SYSTEMS'):
        systems = LatticeParameterCalculator.CRYSTAL_SYSTEMS
        print(f"   ✅ CRYSTAL_SYSTEMS found ({len(systems)} systems)")
        for key in ['cubic_FCC', 'cubic_BCC', 'Hexagonal']:
            if key in systems:
                print(f"   ✅ System '{key}' available")
    else:
        print("   ❌ CRYSTAL_SYSTEMS not found")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\n🎉 batch_cal_volume.py is ready to use!")
    print("\n📝 Quick start:")
    print("   from batch_cal_volume import LatticeParameterCalculator")
    print("   calculator = LatticeParameterCalculator(wavelength=0.4133)")
    print("   results = calculator.calculate('your_peaks.csv')")
    print("\n")
    
except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

