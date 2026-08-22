"""
Sort a .txt file with two numbers per row.
Sorts by first number (primary), then by second number (secondary), both ascending.
"""

def sort_two_column_file(input_file, output_file=None):
    """
    Sort a text file with two numbers per row.
    
    Parameters:
    -----------
    input_file : str
        Path to the input .txt file
    output_file : str, optional
        Path to the output file. If None, overwrites the input file.
    """
    if output_file is None:
        output_file = input_file
    
    # Read and parse the file
    rows = []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        first = float(parts[0])
                        second = float(parts[1])
                        rows.append((first, second, line))
                    except ValueError:
                        print(f"Warning: Could not parse line: {line}")
    
    # Sort by first number, then by second number
    rows.sort(key=lambda x: (x[0], x[1]))
    
    # Write sorted rows to output file
    with open(output_file, 'w') as f:
        for first, second, original_line in rows:
            f.write(original_line + '\n')
    
    print(f"Sorted {len(rows)} rows and saved to: {output_file}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python sort_txt_file.py <input_file> [output_file]")
        print("Example: python sort_txt_file.py data.txt")
        print("         python sort_txt_file.py data.txt sorted_data.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    sort_two_column_file(input_file, output_file)
