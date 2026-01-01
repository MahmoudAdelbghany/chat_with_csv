import sys
import os
sys.path.append(os.getcwd())

from agent.executor import run_code_capture

def test_artifact_capture():
    print("Testing artifact capture...")
    
    code = """
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.savefig(f"{output_dir}/test_plot.png")
print("Plot saved")
    """
    
    # We don't need to inject output_dir manually, executor does it.
    result = run_code_capture(code)
    
    print("Stdout:", result.stdout)
    print("Error:", result.error)
    print("Artifacts:", result.artifacts)
    
    if result.error:
        print("FAILED: Error during execution")
        sys.exit(1)
        
    if not result.artifacts:
        print("FAILED: No artifacts captured")
        sys.exit(1)
        
    if not result.artifacts[0].endswith("test_plot.png"):
        print("FAILED: Incorrect artifact name")
        sys.exit(1)
        
    print("SUCCESS: Artifact captured correctly")

if __name__ == "__main__":
    test_artifact_capture()
