import argparse

def format_hex_data(input_file_path, output_file_path):
    with open(input_file_path, 'r') as input_file, open(output_file_path, 'w') as output_file:
        for line in input_file:
            parts = line.strip().split()  # Split line into parts
            if parts:  # Check if there are any parts
                selected_part = parts[0]  # Choose the part you want, e.g., the first part
                formatted_part = ' '.join(selected_part[i:i+2] for i in range(0, len(selected_part), 2))
                output_file.write(formatted_part + '\n')  # Write formatted part to output

def main():
    parser = argparse.ArgumentParser(description='Process hex data from input file and format output.')
    parser.add_argument('-i', '--input', required=True, help='Input file path')
    parser.add_argument('-o', '--output', required=True, help='Output file path')

    args = parser.parse_args()
    
    # Call the function with paths provided by user
    format_hex_data(args.input, args.output)

if __name__ == "__main__":
    main()
