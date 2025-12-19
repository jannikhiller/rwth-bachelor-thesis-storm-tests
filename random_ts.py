import random
import os
import subprocess
import re
from tqdm import tqdm


def generate_prism_file(n, filename):
    if n < 2 or n % 2 != 0:
        raise ValueError("Number of states (n) must be an even number and at least 2.")

    # Assign states to players
    states = list(range(n))
    random.shuffle(states)
    tri_states = states[: n // 2]
    sq_states = states[n // 2 :]

    def create_probabilistic_spanning_tree(states):
        transitions = {s: [] for s in states}
        available_states = set(states[1:])  # Exclude state 0 from the list
        connected_states = {0}

        while available_states:
            src = random.choice(list(connected_states))
            dest = available_states.pop()
            connected_states.add(dest)

            if random.choice([True, False]) and len(connected_states) > 1:
                other_dest = random.choice(list(connected_states))
                transitions[src].append((dest, other_dest))
            else:
                transitions[src].append(dest)

        return transitions

    def add_extra_transitions(states, transitions):
        for src in states:
            num_additional = random.randint(1, 2)
            for _ in range(num_additional):
                successors = random.sample(states, random.choice([1, 2]))
                if len(successors) == 1:
                    transitions[src].append(successors[0])
                else:
                    transitions[src].append((successors[0], successors[1]))

    def format_transitions(state, successors):
        lines = []
        for succ in successors:
            if isinstance(succ, tuple):
                lines.append(
                    f"[] state={state} -> 1/2 : (state'={succ[0]}) + 1/2 : (state'={succ[1]});"
                )
            else:
                lines.append(f"[] state={state} -> (state'={succ});")
        return lines

    transitions = create_probabilistic_spanning_tree(states)
    add_extra_transitions(states, transitions)

    with open(filename, "w") as f:
        f.write("smg\n\n")
        f.write("player tri m_tri endplayer\n")
        f.write("player sq m_sq endplayer\n\n")
        f.write(f"global state : [0..{n - 1}] init 0;\n\n")

        f.write("module m_tri\n")
        for state in tri_states:
            for line in format_transitions(state, transitions[state]):
                f.write(f"  {line}\n")
        f.write("endmodule\n\n")

        f.write("module m_sq\n")
        for state in sq_states:
            for line in format_transitions(state, transitions[state]):
                f.write(f"  {line}\n")
        f.write("endmodule\n")


def run_storm_and_find_max_iterations(
    folder="random_prism_files_2", storm_path="./storm_debug", prop_file="random.prop"
):
    max_iterations = 0
    best_file = None
    results = []

    # Get list of PRISM files
    prism_files = [f for f in os.listdir(folder) if f.endswith(".prism")]

    # Progress bar for Storm analysis
    for file in tqdm(prism_files, desc="Analyzing PRISM files with Storm", leave=True):
        file_path = os.path.join(folder, file)
        result = subprocess.run(
            [storm_path, "--prism", file_path, "--prop", prop_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = result.stdout

        # Extract iterations using regex
        weak_attractor_match = re.search(
            r"Computing weak attractors took (\d+) iterations", output
        )
        total_iterations = int(weak_attractor_match.group(1))
        results.append((file_path, total_iterations))

        if total_iterations > max_iterations:
            max_iterations = total_iterations
            best_file = file_path
        tqdm.write(f"{file}: {total_iterations} iterations")

    # Print all results sorted by iterations
    print("\nAll files and their iterations:")
    for file, iterations in sorted(results, key=lambda x: x[1], reverse=True):
        print(f"{file}: {iterations} iterations")

    print(
        f"\nFile with the highest total iterations: {best_file} ({max_iterations} iterations)"
    )
    return best_file, max_iterations


# Generate files
def generate_multiple_files_and_find_max(
    num_files=20000,
    n=6,
    folder="random_prism_files",
    storm_path="./storm_debug",
    prop_file="random.prop",
):
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Progress bar for file generation
    for i in tqdm(range(num_files), desc="Generating PRISM files"):
        filename = os.path.join(folder, f"random_{i:05}.prism")
        generate_prism_file(n=n, filename=filename)

    return run_storm_and_find_max_iterations(
        folder=folder, storm_path=storm_path, prop_file=prop_file
    )


# Generate files and find the one with the most iterations
if __name__ == "__main__":
    generate_multiple_files_and_find_max()
