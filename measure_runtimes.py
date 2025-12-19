#!/usr/bin/env python

import csv
import sys
import math
from pathlib import Path
import logging
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from compare import get_prism_result, get_storm_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(
    input_dir=Path("bad_runtime_example"), output_csv=Path("bad_runtime_example.csv")
):
    # PRISM and STORM executables
    prism_executable = Path("./prism")  # Adjust as needed
    storm_executable = Path("./storm")  # Adjust as needed

    # Collect data for CSV
    data = []
    test_cases = sorted(input_dir.glob("*.prism"))

    # Set up progress bar
    with tqdm(
        total=len(test_cases), desc="Processing test cases", unit="test case"
    ) as pbar:
        for model_file in test_cases:
            # Identify the corresponding property file
            test_case_size = int(
                model_file.stem
            )  # Assuming sizes are indicated by the file stem
            prop_file = Path(input_dir.stem + ".prop")

            if not prop_file.exists():
                logger.warning(f"Property file not found for {model_file}. Skipping.")
                pbar.update(1)
                continue

            # Check if the .prism file starts with "mdp"
            with open(model_file, "r") as f:
                first_line = f.readline().strip()
                is_mdp = first_line.startswith("mdp")

            logger.info(f"Processing test case size {test_case_size}")

            try:
                # Run PRISM
                _, prism_timing = get_prism_result(
                    model_file, prop_file, constants=None, executable=prism_executable
                )
                _, prism_symbolic_timing = get_prism_result(
                    model_file,
                    prop_file,
                    constants=None,
                    executable=prism_executable,
                    use_symbolic=True,
                )

                # Run Storm
                _, storm_timing = get_storm_result(
                    model_file, prop_file, constants=None, executable=storm_executable
                )

                # If "mdp", run symbolic checking with Storm
                if is_mdp:
                    _, storm_symbolic_timing = get_storm_result(
                        model_file,
                        prop_file,
                        constants=None,
                        executable=storm_executable,
                        use_symbolic=True,
                    )
                    storm_symbolic_time = storm_symbolic_timing.get(
                        "model_checking", math.inf
                    )
                    storm_symbolic_model_building_time = storm_symbolic_timing.get(
                        "model_construction", math.inf
                    )
                else:
                    storm_symbolic_time = "N/A"
                    storm_symbolic_model_building_time = "N/A"

                # Extract timings
                prism_time = prism_timing.get("prob0", math.inf) + prism_timing.get(
                    "prob1", math.inf
                )
                prism_model_building_time = prism_timing.get(
                    "model_construction", math.inf
                )

                prism_symbolic_time = prism_symbolic_timing.get(
                    "prob0", math.inf
                ) + prism_symbolic_timing.get("prob1", math.inf)
                prism_symbolic_model_building_time = prism_symbolic_timing.get(
                    "model_construction", math.inf
                )

                storm_time = storm_timing.get("model_checking", math.inf)
                storm_model_building_time = storm_timing.get(
                    "model_construction", math.inf
                )

                time_measurements = [
                    "N/A" if t == math.inf else f"{t:.3f}"
                    for t in [
                        storm_model_building_time,
                        storm_time,
                        storm_symbolic_model_building_time,
                        storm_symbolic_time,
                        prism_model_building_time,
                        prism_time,
                        prism_symbolic_model_building_time,
                        prism_symbolic_time,
                    ]
                ]
                data.append((test_case_size, *time_measurements))

            except Exception as e:
                logger.error(f"Error processing {model_file} and {prop_file}: {e}")
            finally:
                pbar.update(1)

    # Write results to CSV
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "number_of_states",
                "storm_model_building",
                "storm_reachability",
                "storm_symbolic_model_building",
                "storm_symbolic_reachability",
                "prism_model_building",
                "prism_reachability",
                "prism_symbolic_model_building",
                "prism_symbolic_reachability",
            ]
        )

        writer.writerows(sorted(data, key=lambda x: x[0]))

    logger.info(f"Results written to {output_csv}")


if __name__ == "__main__":
    with logging_redirect_tqdm():
        if len(sys.argv) >= 2:
            main(Path("./" + sys.argv[1]), Path(sys.argv[1] + ".csv"))
        else:
            main()
