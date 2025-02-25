"""Script to create (and optionally install) a `.whl` archive for Keras Core.

Usage:

1. Create a `.whl` file in `dist/`:

```
python3 pip_build.py
```

2. Also install the new package immediately after:

```
python3 pip_build.py --install
```
"""
import argparse
import glob
import os
import pathlib
import shutil

import namex

# Needed because importing torch after TF causes the runtime to crash
import torch  # noqa: F401

package = "keras_core"
build_directory = "tmp_build_dir"
dist_directory = "dist"
to_copy = ["setup.py", "README.md"]


def ignore_files(_, filenames):
    return [f for f in filenames if f.endswith("_test.py")]


def build():
    if os.path.exists(build_directory):
        raise ValueError(f"Directory already exists: {build_directory}")

    whl_path = None
    try:
        # Copy sources (`keras_core/` directory and setup files) to build
        # directory
        root_path = pathlib.Path(__file__).parent.resolve()
        os.chdir(root_path)
        os.mkdir(build_directory)
        shutil.copytree(
            package, os.path.join(build_directory, package), ignore=ignore_files
        )
        for fname in to_copy:
            shutil.copy(fname, os.path.join(f"{build_directory}", fname))
        os.chdir(build_directory)

        # Restructure the codebase so that source files live in `keras_core/src`
        namex.convert_codebase(package, code_directory="src")

        # Generate API __init__.py files in `keras_core/`
        namex.generate_api_files(package, code_directory="src", verbose=True)

        # Make sure to export the __version__ string
        from keras_core.src.version import __version__  # noqa: E402

        with open(os.path.join(package, "__init__.py")) as f:
            init_contents = f.read()
        with open(os.path.join(package, "__init__.py"), "w") as f:
            f.write(init_contents + "\n\n" + f'__version__ = "{__version__}"\n')

        # Build the package
        os.system("python3 -m build")

        # Save the dist files generated by the build process
        os.chdir(root_path)
        if not os.path.exists(dist_directory):
            os.mkdir(dist_directory)
        for fpath in glob.glob(
            os.path.join(build_directory, dist_directory, "*.*")
        ):
            shutil.copy(fpath, dist_directory)

        # Find the .whl file path
        for fname in os.listdir(dist_directory):
            if fname.endswith(".whl"):
                whl_path = os.path.abspath(os.path.join(dist_directory, fname))
        print(f"Build successful. Wheel file available at {whl_path}")
    finally:
        # Clean up: remove the build directory (no longer needed)
        shutil.rmtree(build_directory)
    return whl_path


def install_whl(whl_fpath):
    print(f"Installing wheel file: {whl_fpath}")
    os.system(f"pip3 install {whl_fpath} --force-reinstall --no-dependencies")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install",
        action="store_true",
        help="Whether to install the generated wheel file.",
    )
    args = parser.parse_args()
    whl_path = build()
    if whl_path and args.install:
        install_whl(whl_path)
