#!/usr/bin/env python
import yaml as YAML
import proj_conf
import os
import click
import shutil
import docker
import subprocess
import sys

docker_client = docker.from_env()
dir = os.getcwd()

def load_proj():
    yaml = {}

    if os.path.exists('proj.yaml'):
        with open('proj.yaml') as proj_file:
            yaml = YAML.load(proj_file)
            if 'type' not in yaml or yaml['type'] != 'tofu_build':
                raise Exception("Unknown project type!")
    else:
        raise Exception("Unable to find project!")
    return yaml


proj_settings = load_proj()
dev_image = proj_settings['project']['name'] + "_dev"
prod_image = proj_settings['project']['name'] + "_prod"

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

    print "Preparing docker image [%s]" % name
    if subprocess.Popen(
            ["docker", "build", "-f", docker_file, "-t", img, "."],
            stdin=file,
            stdout=file,
            stderr=file,
    ).wait() != 0:
        print "Build failed!"
        sys.exit(1)
    print "Image ready"

    print "Running docker image [%s]" % name
    if subprocess.Popen(
            docker_run,
            stdin=file,
            stdout=file,
            stderr=file,
    ).wait() != 0:
        print "Build failed!"
        sys.exit(1)

    print "Build successful!"


@click.command()
@click.option('--production', is_flag=True)
@click.option('--verbose', is_flag=True)
def build(production, verbose):
    print production
    print verbose
    print "Initializing..."
    stop()
    del_containers()
    print "Building new config..."
    make_config(False)

    if not os.path.exists("build"):
        os.makedirs("build")

    pipe = False
    if verbose:
        pipe = True

    run_env("dev", pipe)

    if production:
        run_env("prod", pipe)

    print
    print "**************************"
    print "Your build was succesful!"
    print "**************************"
    print


cli.add_command(clean)
cli.add_command(config)
cli.add_command(build)

cli()