import pystache


def __docker_build_template():
    return """{{#environment}}
FROM ubuntu:{{ubuntu_ver}}

ENV DEBIAN_FRONTEND=noninteractive 
RUN apt-get update -y
RUN apt-get install -y software-properties-common python-software-properties
{{#ppas}}
RUN add-apt-repository -y ppa:{{.}}
{{/ppas}}
{{#build_ppas}}
RUN add-apt-repository -y ppa:{{.}}
{{/build_ppas}}
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN apt-get update -y
RUN apt-get install -y {{compiler}} cmake build-essential
{{#build_pckgs}}
RUN apt-get install -y {{.}}
{{/build_pckgs}}
{{#pckgs}}
RUN apt-get install -y {{.}}
{{/pckgs}}

{{#cmds}}
RUN {{.}}
{{/cmds}}

VOLUME {{volume}}
WORKDIR {{volume}}

ENV CONFIG_TIME="{{timestamp}}"

{{/environment}}

RUN rm -rf build
RUN mkdir -p build
WORKDIR build

{{#project}}
ENV PROJECT={{name}}
{{/project}}

CMD ["bash", "../cmake.sh"]
"""


def __docker_run_template_min():
    return """{{#environment}}
FROM ubuntu:{{ubuntu_ver}}

ENV CONFIG_TIME="{{timestamp}}"

COPY build {{volume}}
WORKDIR {{volume}}
WORKDIR bin

RUN chmod +x prod_tests.sh
RUN ./prod_tests.sh

{{/environment}}

{{#project}}
ENV PROJECT={{name}}
CMD ["./{{main}}"]
{{/project}}
"""


def __docker_run_template_install():
    return """
{{#environment}}
FROM ubuntu:{{ubuntu_ver}}

RUN apt-get update -y
RUN apt-get install -y software-properties-common python-software-properties
{{#ppas}}
RUN add-apt-repository -y ppa:{{.}}
{{/ppas}}
{{#prod_ppas}}
RUN add-apt-repository -y ppa:{{.}}
{{/prod_ppas}}
RUN apt-get update -y
{{#prod_pckgs}}
RUN apt-get install -y {{.}}
{{/prod_pckgs}}
{{#pckgs}}
RUN apt-get install -y {{.}}
{{/pckgs}}

ENV CONFIG_TIME="{{timestamp}}"

COPY build {{volume}}
WORKDIR {{volume}}
WORKDIR bin

{{/environment}}

RUN chmod +x prod_tests.sh
RUN ./prod_tests.sh

{{#project}}
ENV PROJECT={{name}}
CMD ["./{{main}}"]
{{/project}}
"""


def __make_docker_build(yaml):
    with open("Dockerfile_build", "w") as out_file:
        out_file.write(pystache.render(__docker_build_template(), yaml))


def __make_docker_run(yaml):
    template_func = __docker_run_template_install
    env = yaml['environment']

    if len(env['ppas']) == 0 and len(env['pckgs']) == 0 and \
       len(env['prod_ppas']) == 0 and len(env['prod_pckgs']) == 0:
        template_func = __docker_run_template_min

    with open("Dockerfile_run", "w") as out_file:
        out_file.write(pystache.render(template_func(), yaml))


def make(yaml):
    __make_docker_build(yaml)
    __make_docker_run(yaml)
