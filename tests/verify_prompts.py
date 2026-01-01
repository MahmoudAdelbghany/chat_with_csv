
import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

from agent.prompts import format_system_prompt

def test_format_system_prompt():
    cols = ["col1", "col2"]
    try:
        prompt = format_system_prompt(cols)
        print("Successfully formatted prompt!")
        # Check if output_dir is preserved correctly in the example
        if '{output_dir}' in prompt:
            print("FAILED: {output_dir} is still present in the prompt (it should have been formatted or ignored?)")
            # Wait, if I escaped it as {{output_dir}}, then .format() turns it into {output_dir}.
            # The LLM SHOULD see {output_dir}.
            # So if it IS present, that is GOOD.
            
        if 'col1, col2' in prompt:
             print("Columns correctly inserted.")
             
    except KeyError as e:
        print(f"FAILED: KeyError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"FAILED: Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_format_system_prompt()
