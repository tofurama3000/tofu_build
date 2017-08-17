import yaml as YAML
import proj_conf
import os
import sys


if len(sys.argv) > 1 and sys.argv[1] == "clean":
    output_files = [
        "build.sh",
        "build_prod.sh",
        "cmake.sh",
        "CMakeLists.txt",
        "Dockerfile_build",
        "Dockerfile_run",
        "prod_tests.sh",
        "setup.sh"
    ]
    for fl in output_files:
        if os.path.exists(fl):
            os.remove(fl)
else:
    yaml = {}

    if os.path.exists('proj.yaml'):
        with open('proj.yaml') as proj_file:
            yaml = YAML.load(proj_file)

    proj_conf.config_proj(yaml)
