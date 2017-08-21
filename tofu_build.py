#!/usr/bin/env python
import yaml
import proj_conf
import os
import click
import shutil
import docker
import subprocess
import sys
import re

docker_client = docker.from_env()
dir = os.getcwd()
yaml_file = 'tofu_proj.yaml'


def load_proj():
    proj_conf = {}
    if os.path.exists(yaml_file):
        with open(yaml_file) as proj_file:
            proj_conf = yaml.load(proj_file)
            if 'type' not in proj_conf or proj_conf['type'].strip() != 'tofu_build':
                raise EnvironmentError("Unknown project type!")
    else:
        raise EnvironmentError("Unable to find project!")
    return proj_conf


try:
    proj_settings = load_proj()
    dev_image = proj_settings['project']['name'] + "_dev"
    prod_image = proj_settings['project']['name'] + "_prod"
except EnvironmentError:
    if click.confirm("Project not initialized, initialize project now?"):
        proj_conf = dict()
        proj_info = dict()
        proj_info['name'] = click.prompt("Enter project name").encode('utf-8')
        proj_info['main'] = re.sub(
            '[^0-9a-zA-Z]+',
            '_',
            proj_info['name'].lower()
        )
        proj_conf['project'] = proj_info
        env_info = dict()
        pckgs = click.prompt(
            "Enter packages to install as comma-separated list"
        ).encode('utf-8')
        env_info['pckgs'] = [pckg.strip() for pckg in pckgs.split(',')]
        proj_conf['environment']= env_info

        app_info = {
            'name': proj_info['main'],
            'sources': [src.strip() for src in
                        click.prompt('Enter source files as comma-separated list')
                            .encode('utf-8')
                            .split(',')
                        ]
        }

        if click.confirm("Do you want to link dynamic libraries?"):
            app_info['dyn_libs'] = {'find': [lib.strip() for lib in click.prompt(
                    'Enter dynamic library CMake names as comma-separated list'
                ).encode('utf-8').split(',')
            ]}

        if click.confirm("Do you want to enable pthreads?"):
            app_info['other_flags'] = [].append('-pthread'.encode('utf-8'))

        proj_conf['apps'] = [app_info]

        num_tests = click.prompt(
            "How many test programs do you have",
            type=int
        )

        tests = []
        for i in range(0, num_tests):
            click.secho("Grabbing info for test %d" % (i + 1), fg='cyan')
            test_info = {
                'name': click.prompt("Enter test name").encode('utf-8'),
                'sources': [src.strip() for src in
                        click.prompt('Enter source files as comma-separated list')
                            .encode('utf-8')
                            .split(',')
                            ]
            }
            if click.confirm("Do you want to link dynamic libraries?"):
                test_info['dyn_libs'] = {
                    'find': [lib.strip() for lib in click.prompt(
                        'Enter dynamic library CMake names as comma-separated list'
                    ).encode('utf-8').split(',')
                ]}
            if click.confirm("Do you want to enable pthreads?"):
                test_info['other_flags'] = [].append('-pthread'.encode('utf-8'))
            tests.append(test_info)

        proj_conf['tests'] = tests

        with open(yaml_file, "w") as proj_file:
            click.secho("Saving config...", fg='green')
            proj_file.write(yaml.dump(proj_conf))
        click.secho("Done", fg='green')
    else:
        click.secho("Exiting...", fg='red')
        exit(0)


@click.group()
def cli():
    pass


def stop():
    try:
        cont = docker_client.containers.get(dev_image)
        cont.stop()
    except:
        pass

    try:
        cont = docker_client.containers.get(prod_image)
        cont.stop()
    except:
        pass


def del_containers():
    try:
        cont = docker_client.containers.get(dev_image)
        cont.remove()
    except:
        pass

    try:
        cont = docker_client.containers.get(prod_image)
        cont.remove()
        cont.stop()
    except:
        pass


def del_images():
    try:
        docker_client.images.remove(dev_image)
    except:
        pass

    try:
        docker_client.images.remove(prod_image)
    except:
        pass


@click.command()
def clean():
    print "Cleaning..."
    output_files = [
        "build.sh",
        "build_prod.sh",
        "cmake.sh",
        "CMakeLists.txt",
        "Dockerfile_build",
        "Dockerfile_run",
        "prod_tests.sh"
    ]
    for fl in output_files:
        if os.path.exists(fl):
            os.remove(fl)
    if os.path.exists('build'):
        try:
            shutil.rmtree('build')
        except:
            print "Unable to delete build tree, remove tree with root privileges"
    stop()
    del_containers()
    del_images()

    print "Clean done."


def make_config(legacy):
    options = {}
    if legacy:
        options['legacy'] = True
    proj_conf.config_proj(proj_settings, options)


@click.command()
@click.option('--legacy', is_flag=True)
def config(legacy):
    make_config(legacy)


def run_env(env, pipe):
    img = dev_image
    name = "Development"
    file=subprocess.PIPE
    docker_file = "Dockerfile_build"
    docker_run = ["docker", "run", "-v", dir + ":/root/app", img]
    if env == "prod":
        img = prod_image
        name = "Production"
        docker_file = "Dockerfile_run"
        docker_run = ["docker", "run", img]

    if pipe:
        file = sys.stdout

    click.secho("Preparing docker image [%s]" % name, fg='yellow')
    if subprocess.Popen(
            ["docker", "build", "-f", docker_file, "-t", img, "."],
            stdin=file,
            stdout=file,
            stderr=file,
    ).wait() != 0:
        click.secho("Build failed!", fg='red')
        sys.exit(1)
    click.echo("Image ready")

    click.secho("Running docker image [%s]" % name, fg='yellow')
    if subprocess.Popen(
            docker_run,
            stdin=file,
            stdout=file,
            stderr=file,
    ).wait() != 0:
        click.secho("Build failed!", fg='red')
        sys.exit(1)

    click.secho("Build successful!", fg='green')


@click.command()
@click.option('--production', is_flag=True)
@click.option('--verbose', is_flag=True)
def build(production, verbose):
    print production
    print verbose
    click.echo("Initializing...")
    stop()
    del_containers()
    click.echo("Building new config...")
    make_config(False)

    if not os.path.exists("build"):
        os.makedirs("build")

    pipe = False
    if verbose:
        pipe = True

    run_env("dev", pipe)

    if production:
        run_env("prod", pipe)

    click.echo()
    click.secho("***************************", fg='green')
    click.secho(" Your build was succesful! ", fg='green')
    click.secho("***************************", fg='green')
    click.echo()


def print_info(info, tabs=0, print_func=None, tab="\t"):
    def prnt(statement):
        tbs = ""
        for i in range(tabs):
            tbs += tab
        if print_func is None:
            click.echo("%s%s" % (tbs, statement))
        else:
            print_func("%s%s" % (tbs, statement))

    if isinstance(info, dict):
        if 'desc' not in info:
            keys = info.keys()
            keys.sort()
            for k in keys:
                prnt(k)
                print_info(info[k], tabs+1, print_func, tab)
        else:
            print_info(
                "Description: %s " % info['desc'],
                tabs,
                print_func,
                tab
            )
            if 'default' in info:
                print_info(
                    "Default value: %s" % str(info['default']),
                    tabs,
                    print_func,
                    tab
                )
            else:
                print_info(
                    "[ REQUIRED ]",
                    tabs,
                    print_func,
                    tab
                )
    elif isinstance(info, (list, tuple)):
        for v in info:
            print_info(
                v,
                tabs + 1,
                print_func,
                tab
            )
    else:
        prnt(info)


class InternalStringAppend:
    def __init__(self):
        self.str = ""

    def append(self, str):
        self.str += str + "\n"

    def get(self):
        return self.str


@click.command()
def instructions():
    instructions = proj_conf.proj_instructions()
    print_info(instructions)


@click.command()
def build_man():
    str = InternalStringAppend()
    print_info(proj_conf.proj_instructions(), print_func=str.append, tab="    ")
    man_page = """
." Manpage for tofu_build'
.TH tofu_build 1 "21 Aug 2017" "v0.1" "tofu_build man page"
.SH NAME
tofu_build \\- Runs the TofuSoftware build system
.SH SYNOPSIS
tofu_build [OPTIONS] ACTION
.SH DESCRIPTION
tofu_build is a build system built around CMake and Docker. It creates two docker containers, one for building the application and one for running it. It manages the project configuration for both containers, allowing a centralized location for managing the configuration for two devices. It also generates CMakeLists.txt for use in the build Docker container. Unit tests are ran in both containers. The script also manages the build process by building and running the Docker images and checking at each step to make sure everything succeeds before moving on to the next step. The script also handles clean-up of docker containers and generated files (docker images are kept for faster future builds, those need to be cleaned manually). Currently only C++ is supported, but there are plans for other languages to be added in the future.
.SH ACTIONS
Below is a list of actions for the application:
    - clean
        The clean command will clean generated files and attempt to clean the build folder. However, due to permissions with mounted volumes, you may need to manually remove the build folder as root.
    - config
        This will create just the configuration files. It is called automatically by build.
        
        Options:
            --legacy - If present, tofu_bulid will output the legacy config files where you run the build.sh file manually to start the bulid process. This has been deprecated and will be removed by version 1.0
    - build
        This builds the project located in the current working directory.
        
        Options:
            --production - If present, tofu_bulid will build and test the production Docker environment, otherwise it will only test the build docker image
            --verbose - If present, will enable verbose mode
    - instructions
        Will print out project file specifications
.SH PROJECT FILE
The project file for tofu_build has the YAML format. It controls steps used when configuring the Docker images and creating the CMakeLists.txt file, including what packages will be installed, commands to run, libraries to link, etc. The format is outlined below

""" + str.get() + """

.SH SEE ALSO
For further information, see the README.md file
.SH BUGS
Bugs and issues will be tracked at https://github.com/tofurama3000/tofu_build/issues
.SH AUTHOR
Matthew Tolman (aka tofurama3000) https://github.com/tofurama3000
"""
    with open('tofu_build', 'w') as man_page_fd:
        man_page_fd.write(man_page)


cli.add_command(clean)
cli.add_command(config)
cli.add_command(build)
cli.add_command(instructions)
cli.add_command(build_man)

cli()