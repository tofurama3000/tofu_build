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
            if 'type' not in proj_conf or proj_conf['type'] != 'tofu_build':
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


cli.add_command(clean)
cli.add_command(config)
cli.add_command(build)

cli()