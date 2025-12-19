import sys


def generate_bad_runtime_example(n: int) -> tuple[str, str]:
    transitions: list[str] = []

    for i in range(n):
        transitions.append(f"[] state={i} -> (state'={i});")
        if i < n - 1:
            transitions.append(
                f"[] state={i} -> 1/2 : (state'={i+1}) + 1/2 : (state'=0);"
            )

    prism_file = f"""smg

global state: [0..{n-1}] init 0;

player sq m_sq endplayer

module m_sq
  {"\n  ".join(transitions)}
endmodule
"""

    property_file = f"""P>=1 [ F state=0 ]"""

    return prism_file, property_file


def main() -> None:
    if len(sys.argv) >= 2:
        ns = list(map(int, sys.argv[1:]))
    else:
        ns = [5]

    for n in ns:
        prism_file, property_file = generate_bad_runtime_example(n)
        with open(f"bad_runtime_example/{n:05}.prism", "w") as f:
            f.write(prism_file)
        with open(f"bad_runtime_example/{n:05}.prop", "w") as f:
            f.write(property_file)


if __name__ == "__main__":
    main()
