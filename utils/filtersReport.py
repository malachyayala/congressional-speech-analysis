import json
import sys
import datetime

# --- CONFIGURATION ---
FILTERS_PATH = "filters.json"
OUTPUT_FILE = "gem_context_report.txt"

def print_error_context(filepath, error):
    """
    Reads the file and prints the exact lines where the error happened
    so you can spot the typo (like a missing quote or trailing comma).
    """
    print(f"\n❌ JSON SYNTAX ERROR: {error.msg}")
    print(f"   Line {error.lineno}, Column {error.colno}")
    print("-" * 40)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Get a window of lines around the error
        start = max(0, error.lineno - 3)
        end = min(len(lines), error.lineno + 2)
        
        for i in range(start, end):
            prefix = ">> " if i + 1 == error.lineno else "   "
            print(f"{prefix}{i+1}: {lines[i].rstrip()}")
            
        print("-" * 40)
        print("💡 TIP: Look for trailing commas (,) or single quotes (')!")
    except Exception as e:
        print(f"Could not read file context: {e}")

def generate_report(data):
    """
    Creates a timestamped report of your current settings.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write(f"CONGRESSIONAL ANALYSIS CONFIGURATION REPORT\n")
        out.write(f"Generated: {timestamp}\n")
        out.write("=================================================\n\n")

        # --- SECTION 1: POLICY BRIDGE ---
        if "policy_bridge" in data:
            count = len(data["policy_bridge"])
            out.write(f"SECTION 1: POLICY TOPICS ({count} Categories)\n")
            out.write("Matches historical language to modern policy buckets.\n\n")
            
            for category, content in data["policy_bridge"].items():
                terms = content.get("historical_terms", [])
                desc = content.get("description", "N/A")
                
                out.write(f"[{category.upper()}]\n")
                out.write(f"   • Description: {desc}\n")
                out.write(f"   • Term Count:  {len(terms)}\n")
                # Show first 5 and last 5 terms to help verify additions
                if len(terms) > 10:
                    preview = ", ".join(terms[:5]) + " ... " + ", ".join(terms[-5:])
                else:
                    preview = ", ".join(terms)
                out.write(f"   • Terms:       {preview}\n\n")
        else:
            out.write("⚠️ SECTION 1: POLICY BRIDGE MISSING!\n\n")

        # --- SECTION 2: DENOISING ---
        if "denoising_lexicon" in data:
            out.write("SECTION 2: DENOISING LEXICON\n")
            out.write("Filters used to strip noise and procedural garbage.\n\n")
            
            for list_name, terms in data["denoising_lexicon"].items():
                if isinstance(terms, list):
                    out.write(f"[{list_name.upper()}]\n")
                    out.write(f"   • Count: {len(terms)}\n")
                    preview = ", ".join(terms[:8]) + ("..." if len(terms) > 8 else "")
                    out.write(f"   • Sample: {preview}\n\n")
        else:
            out.write("⚠️ SECTION 2: DENOISING LEXICON MISSING!\n\n")

    print(f"\n✅ SUCCESS: Configuration is valid.")
    print(f"📄 Detailed report saved to: {OUTPUT_FILE}")
    print(f"   (Open this file to see exactly what you just changed)")

def main():
    print(f"🔍 Validating {FILTERS_PATH}...")
    try:
        with open(FILTERS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # If load succeeds, generate the report
        generate_report(data)

    except json.JSONDecodeError as e:
        # If load fails, show the context
        print_error_context(FILTERS_PATH, e)
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: {FILTERS_PATH} not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()