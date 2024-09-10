#!/usr/bin/env python

import argparse
import logging
from pathlib import Path
from typing import NamedTuple
from collections import namedtuple
import json
import subprocess
import time
import os

logger = logging.getLogger(__name__)


def get_prism_state_numbering(state_file: Path) -> list[NamedTuple]:
    with open(state_file) as open_file:
        header, *data = open_file.read().splitlines()

    variable_names = header[1:-1].split(",")
    variable_names_order = sorted(
        range(len(variable_names)), key=lambda i: variable_names[i]
    )
    State = namedtuple("State", [variable_names[i] for i in variable_names_order])
    def get_value(s):
        try:
            return int(s)
        except ValueError:
            return s == "true"

    out = []
    for i, line in enumerate(data):
        number_str, state_str = line.split(":")
        assert int(number_str) == i
        values = list(map(get_value, state_str[1:-1].split(",")))
        ordered_values = (values[i] for i in variable_names_order)
        out.append(State._make(ordered_values))

    return out


def get_prism_result(
    model_file: Path,
    prop_file: Path,
    constants: list[str] | None,
    executable: Path = Path("./prism"),
) -> dict[NamedTuple, bool]:
    working_folder = Path("tmp/prism-games/")
    os.makedirs(working_folder, exist_ok=True)

    args = [
            model_file,
            prop_file,
            "-exportvector",
            working_folder / "result",
            "-exportstates",
            working_folder / "states",
            ]
    if constants is not None:
        args.extend(("-const", ",".join(constants)))

    logger.info("Running prism-games.")
    t0 = time.time()
    result = subprocess.run(
        [
            executable.absolute(),
            *args
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    t1 = time.time()
    logger.info(f"Finished in {t1 - t0:.2f}s.")
    logger.debug(result.stdout.decode())

    if result.returncode != 0:
        logger.error(f"PRISM failed with exit code {result.returncode}")
        return {}

    with open(working_folder / "result") as open_file:
        result = [line == "true" for line in open_file.read().splitlines()]
    states = get_prism_state_numbering(working_folder / "states")

    return dict(zip(states, result))


def prepare_storm_prop(prop_file: Path, working_dir: Path) -> Path:
    target_path = working_dir / "prepared.prop"
    with open(prop_file) as in_file, open(target_path, "w") as out_file:
        out_file.write("\n".join(f"filter(values, {prop}, true)" for prop in in_file))
    return target_path


def get_storm_result(
    model_file: Path,
    prop_file: Path,
    constants: list[str] | None,
    executable: Path = Path("./storm"),
) -> dict[NamedTuple, bool]:
    working_folder = Path("tmp/storm/")
    os.makedirs(working_folder, exist_ok=True)
    prop_file = prepare_storm_prop(prop_file, working_folder)
    args = [
            "--prism",
            model_file,
            "--prop",
            prop_file,
            "--exportresult",
            working_folder / "result",
            "--buildstateval"
            ]
    if constants is not None:
        args.extend(("--constants", ",".join(constants)))

    logger.info("Running storm.")
    t0 = time.time()
    result = subprocess.run(
        [
            executable.absolute(),
            *args
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    t1 = time.time()
    logger.info(f"Finished in {t1 - t0:.2f}s.")
    logger.debug(result.stdout.decode())

    if result.returncode != 0:
        logger.error(f"STORM failed with exit code {result.returncode}")
        return {}

    with open(working_folder / "result") as open_file:
        result = json.load(open_file)

    State = namedtuple("State", sorted(result[0]["s"]))

    states = (State._make(entry["s"][var] for var in State._fields) for entry in result)
    values = (entry["v"] for entry in result)
    return dict(zip(states, values))


def compare_results(prism_result: dict[NamedTuple, bool], storm_result: dict[NamedTuple, bool], num_printed_elements: int=5) -> bool:
    logger.debug("PRISM Result: %s", prism_result)
    logger.debug("STORM Result: %s", storm_result)

    keys_of_differing_values = set(
        k for k, _ in (set(prism_result.items()) ^ set(storm_result.items()))
    )
    def get_diff_tuple(k) -> tuple:
        return (k, prism_result.get(k), storm_result.get(k))

    storm_extra_states = []
    prism_extra_states = []
    diff_tuples = []

    for k, prism_v, storm_v in map(get_diff_tuple, keys_of_differing_values):
        if prism_v is None:
            storm_extra_states.append((k, storm_v))
        elif storm_v is None:
            prism_extra_states.append((k, prism_v))
        else:
            diff_tuples.append((k, prism_v, storm_v))

    def get_shortened_list_str(l: list) -> str:
        out = ", ".join(map(str, l[:num_printed_elements]))
        if len(l) > num_printed_elements:
            out += ", ..."
        return out


    if prism_extra_states:
        logger.warning(f"PRISM returned {len(prism_extra_states)} extra states:\n"
                       f"{get_shortened_list_str(prism_extra_states)}")
    if storm_extra_states:
        logger.warning(f"STORM returned {len(storm_extra_states)} extra states:\n"
                       f"{get_shortened_list_str(storm_extra_states)}")
    if diff_tuples:
        logger.warning(
                f"The following states have a different results (state, prism_result, storm_result):\n"
                f"{get_shortened_list_str(diff_tuples)}"
        )
    return not diff_tuples


def main():
    parser = argparse.ArgumentParser(
        description="Run PRISM and STORM tools with specified models and properties."
    )
    parser.add_argument("model_file", type=Path, help="Path to the model file.")
    parser.add_argument("prop_file", type=Path, help="Path to the property file.")
    parser.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="Increase output verbosity (e.g., -v for INFO, -vv for DEBUG).",
    )
    parser.add_argument(
        "-c",
        "--constants",
        nargs="+",
        help="Give a list of constants to the modelcheckers, e.g -c vmin=0 vmax=10",
    )
    parser.add_argument(
            "-s",
            "--storm",
            type=Path,
            default=Path("./storm"),
            help="Provide the storm executable.",
            )
    parser.add_argument(
            "-p",
            "--prism",
            type=Path,
            default=Path("./prism"),
            help="Provide the prism games executable.",
            )

    args = parser.parse_args()

    if args.verbosity >= 2:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbosity >= 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    prism = get_prism_result(args.model_file, args.prop_file, args.constants, args.prism)
    storm = get_storm_result(args.model_file, args.prop_file, args.constants, args.storm)

    if compare_results(prism, storm):
        print("Results match!")
        exit(0)
    else:
        print("Results mismatch!")
        exit(1)


if __name__ == "__main__":
    main()
