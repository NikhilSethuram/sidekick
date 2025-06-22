from typing import List
import sys
import re

def extract_transcript_content(transcript_file: str) -> List[str]:
    """Extract new (non-cumulative) transcript lines from a WhisperLive-style transcript."""
    with open(transcript_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    transcript_lines = []
    last_line = ""

    for line in lines:
        line = line.strip()

        # Skip headers and metadata
        if not line or line.startswith(('=', 'Zoom Meeting', 'Meeting:', 'Meeting ended:')):
            continue

        # Only process actual transcript content
        if '] ' in line and line.startswith('['):
            content = line.split('] ', 1)[1]
        else:
            content = line

        # Get the new part by removing the last_line prefix from current
        if content.startswith(last_line):
            new_part = content[len(last_line):].strip()
        else:
            new_part = content.strip()

        if new_part:
            transcript_lines.append(new_part)

        last_line = content  # Update for next iteration

    return transcript_lines

def update_main_graph(transcript_lines: List[str]) -> None:
    """Update the sample_transcript in main_graph.py with new lines."""
    main_graph_path = 'core/main_graph.py'
    
    with open(main_graph_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the sample_transcript list
    pattern = r'sample_transcript\s*=\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Could not find sample_transcript section in main_graph.py")
    
    # Format new transcript lines
    new_transcript = '[\n        ' + ',\n        '.join(f'"{line}"' for line in transcript_lines) + '\n    ]'
    
    # Replace the old transcript with the new one
    new_content = content[:match.start()] + 'sample_transcript = ' + new_transcript + content[match.end():]
    
    with open(main_graph_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    """Main script execution."""
    if len(sys.argv) != 2:
        print("Usage: python update_transcript.py <transcript_file>")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    try:
        transcript_lines = extract_transcript_content(transcript_file)
        update_main_graph(transcript_lines)
        print(f"✅ Successfully updated main_graph.py with {len(transcript_lines)} lines from {transcript_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()