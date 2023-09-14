# -*- coding: utf-8 -*-

# (C) Copyright 2018- ECMWF.
# (C) Copyright 2022- ETH Zurich.

# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import annotations
import click
import os
import subprocess
from typing import TYPE_CHECKING

from ifs_physics_common.utils.output import print_performance, to_csv

if TYPE_CHECKING:
    from typing import Literal, Optional

    from ifs_physics_common.framework.config import FortranConfig, IOConfig

    from .config import default_fortran_config, default_io_config
else:
    from config import default_fortran_config, default_io_config


def core(config: FortranConfig, io_config: IOConfig) -> None:
    executable = os.path.join(
        os.path.dirname(__file__), config.build_dir, f"bin/dwarf-cloudsc-{config.variant}"
    )
    if not os.path.exists(executable):
        raise RuntimeError(f"The executable `{executable}` does not exist.")

    # warm-up cache
    out = subprocess.run(
        [
            executable,
            str(config.num_threads),
            str(config.num_cols),
            str(min(config.num_cols, config.nproma)),
        ],
        capture_output=True,
    )
    if out.returncode:
        raise RuntimeError(out.stderr.decode("utf-8"))

    # run and profile
    runtime_l = []
    mflops_l = []
    for _ in range(config.num_runs):
        out = subprocess.run(
            [
                executable,
                str(config.num_threads),
                str(config.num_cols),
                str(min(config.num_cols, config.nproma)),
            ],
            capture_output=True,
        )

        if config.variant in ("cuda", "cuda-hoist", "cuda-k-caching"):
            x = out.stdout.decode("utf-8").split("\n")[2]
            y = x.split(" ")
            z = [c for c in y if c != ""]
            runtime_l.append(float(z[-4]))
            mflops_l.append(float(z[-3]))
        elif config.variant in (
            "gpu-omp-scc-hoist",
            "gpu-scc",
            "gpu-scc-cuf",
            "gpu-scc-cuf-k-caching",
            "gpu-scc-hoist",
            "gpu-scc-k-caching",
            "loki-scc-cuf-hoist",
            "loki-scc-hoist",
        ):
            x = out.stderr.decode("utf-8").split("\n")[3]
            y = x.split(" ")
            z = [c for c in y if c != ""]
            runtime_l.append(float(z[-5]))
            mflops_l.append(float(z[-4]))
        else:
            x = out.stderr.decode("utf-8").split("\n")[-2]
            y = x.split(" ")
            z = [c for c in y if c != ""]
            runtime_l.append(float(z[-5]))
            mflops_l.append(float(z[-4]))

    runtime_mean, runtime_stddev, mflops_mean, mflops_stddev = print_performance(
        config.num_cols, runtime_l, mflops_l
    )

    if io_config.output_csv_file is not None:
        to_csv(
            io_config.output_csv_file,
            io_config.host_name,
            config.precision,
            config.variant,
            config.num_cols,
            config.num_threads,
            config.nproma,
            config.num_runs,
            runtime_mean,
            runtime_stddev,
            mflops_mean,
            mflops_stddev,
        )


def _main(
    build_dir: str,
    precision: Literal["double", "single"],
    variant: str,
    nproma: int,
    num_cols: int,
    num_runs: int,
    num_threads: int,
    host_alias: Optional[str],
    output_csv_file: Optional[str],
) -> None:
    """Driver for the FORTRAN implementation of CLOUDSC."""
    config = (
        default_fortran_config.with_build_dir(build_dir)
        .with_precision(precision)
        .with_variant(variant)
        .with_nproma(nproma)
        .with_num_cols(num_cols)
        .with_num_runs(num_runs)
        .with_num_threads(num_threads)
    )
    io_config = default_io_config.with_output_csv_file(output_csv_file).with_host_name(host_alias)
    core(config, io_config)


@click.command()
@click.option(
    "--build-dir",
    type=str,
    default="fortran",
    help="Path to the build directory of the FORTRAN dwarf.",
)
@click.option(
    "--precision",
    type=str,
    default="double",
    help="Select either `double` (default) or `single` precision.",
)
@click.option("--variant", type=str, default="fortran", help="Code variant (default: fortran).")
@click.option(
    "--nproma",
    type=int,
    default=32,
    help="Block size (recommended: 32 on CPUs, 128 on GPUs; default: 32).",
)
@click.option("--num-cols", type=int, default=1, help="Number of domain columns (default: 1).")
@click.option("--num-runs", type=int, default=1, help="Number of executions (default: 1).")
@click.option(
    "--num-threads",
    type=int,
    default=1,
    help="Number of threads (recommended: 24 on Piz Daint's CPUs, 128 on MLux's CPUs, 1 on GPUs; "
    "default: 1).",
)
@click.option("--host-alias", type=str, default=None, help="Name of the host machine (optional).")
@click.option(
    "--output-csv-file",
    type=str,
    default=None,
    help="Path to the CSV file where writing performance counters (optional).",
)
def main(
    build_dir: str,
    precision: Literal["double", "single"],
    variant: str,
    nproma: int,
    num_cols: int,
    num_runs: int,
    num_threads: int,
    host_alias: Optional[str],
    output_csv_file: Optional[str],
) -> None:
    """Driver for the FORTRAN implementation of CLOUDSC."""
    _main(
        build_dir,
        precision,
        variant,
        nproma,
        num_cols,
        num_runs,
        num_threads,
        host_alias,
        output_csv_file,
    )


if __name__ == "__main__":
    main()
