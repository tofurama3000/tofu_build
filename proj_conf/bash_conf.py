import pystache


def __prod_test_template():
    return """#!/usr/bin/env bash

FILES=$(pwd)/*

for f in $FILES
do
    if [[ "$f" = *test_* ]]
    then
        echo "Running test $f..."
        $f
        RES=$?
        if [[ $RES = 0 ]]
        then
            echo "Test $f passed!"
        else
            echo "Test $f failed! CODE: $RES"
            exit $RES
        fi
    fi
done

echo "Tests passed!"
"""


def __build_prod_template():
    return __build_dev_template() + """
{{#project}}

if [ $RES = 0 ]
then
    echo "App '{{name}}' built, building production environment"
    CONTAINERS=docker ps -aq --filter {{name}}_run
    docker stop $CONTAINERS
    docker rm $CONTIANERS
    docker build -t {{name}}_run -f Dockerfile_run .
    RES=$?
else
    echo "App not built. Code $RES"
    exit $RES
fi

if [ $RES = 0 ]
then
    echo "Production environment built for '{{name}}', running..."
    docker run {{name}}_run
    RES=$?
else
    echo "Production environment not built for '{{name}}'. Code $RES"
    exit $RES
fi

echo "Building '{{name}}' [Production] done!"
{{/project}}
"""


def __build_dev_template():
    return """#!/usr/bin/env bash
mkdir -p build

{{#project}}
CONTAINERS=docker ps -aq --filter {{name}}_build
docker stop $CONTAINERS
docker rm $CONTIANERS
docker build -t {{name}}_build -f Dockerfile_build .

RES=$?

if [ $RES = 0 ]
then
    echo "Building app '{{name}}'..."
    docker run -v $(pwd):{{volume}} {{name}}_build
    RES=$?
else
    echo "Could not build build env. Code $RES"
    exit $RES
fi

if [ $RES = 0 ]
then
    echo "Building '{{name}}' [Development] done!"
else
    echo "Building '{{name}}' [Development] failed!"
    exit $RES
fi

{{/project}}
"""


def __cmake_template():
    return """#!/usr/bin/bash env

#yes | rm -rf build/
cmake ..

RES=$?

if [ $RES = 0 ]
then
    echo "CMake successful, testing..."
else
    echo "CMake failed. Code $RES"
    exit $RES
fi

make

RES=$?

if [ $RES = 0 ]
then
    echo "Make successful, testing..."
else
    echo "Make failed. Code $RES"
    exit $RES
fi

make test

RES=$?

if [ $RES = 0 ]
then
    echo "Tests succesful!"
else
    echo "Tests failed. Code $RES"
    exit $RES
fi

echo "Build successful!"
exit $RES
"""


def make(yaml):
    with open("prod_tests.sh", "w") as out_file:
        out_file.write(pystache.render(__prod_test_template(), yaml))
    with open("build.sh", "w") as out_file:
        out_file.write(pystache.render(__build_dev_template(), yaml))
    with open("build_prod.sh", "w") as out_file:
        out_file.write(pystache.render(__build_prod_template(), yaml))
    with open("cmake.sh", "w") as out_file:
        out_file.write(pystache.render(__cmake_template(), yaml))
