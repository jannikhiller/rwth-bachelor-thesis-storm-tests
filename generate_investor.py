import os
import subprocess
import sys


# Function to build the model and retrieve the number of states
def build_model(original_file, vmax):
    """
    Builds the model using PRISM with the given constants and returns the number of states.
    """
    command = ["./prism", original_file, "-const", f"vmax={vmax},vinit={vmax//2}", "-m"]
    process = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    output = process.stdout + process.stderr

    # Parse the number of states from the output
    for line in output.splitlines():
        if line.startswith("States:"):
            states = int(line.split()[1])
            return states

    raise ValueError("Could not determine the number of states from the output.")


# Function to create a modified model file
def create_modified_model(original_file, output_file, vmax):
    """
    Creates a modified copy of the model file with vmax and vinit values replaced.
    """
    with open(original_file, "r") as infile:
        lines = infile.readlines()

    modified_lines = []
    for line in lines:
        if line.startswith("const vmax;"):
            modified_lines.append(f"const int vmax = {vmax};\n")
        elif line.startswith("const vinit;"):
            modified_lines.append(f"const int vinit = {vmax // 2};\n")
        else:
            modified_lines.append(line)

    with open(output_file, "w") as outfile:
        outfile.writelines(modified_lines)


# Main script
if __name__ == "__main__":
    original_file = "investor.prism"
    output_dir = "investor"
    vmax_values = list(map(int, sys.argv[1:]))

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for vmax in vmax_values:
        # Build the model and get the number of states
        try:
            states = build_model(original_file, vmax)
            print(f"Model with vmax={vmax} has {states} states.")

            # Create a new model file with the number of states as the filename
            output_file = os.path.join(output_dir, f"{states:07d}.prism")
            create_modified_model(original_file, output_file, vmax)

        except Exception as e:
            print(f"Error processing vmax={vmax}: {e}")
