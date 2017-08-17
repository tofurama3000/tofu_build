import datetime
import docker_conf
import bash_conf
import cmake_conf


class CallableDefaultFlag:
    def __init__(self, params, func=None):
        if callable(params):
            param_builder = params
            self.params, self.func = param_builder()
        elif func is not None:
            self.params = params
            self.func = func
        else:
            raise "Need to provide a callable" + \
                  " or you need to provide params and func"

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def __default_build_flags():
    def ret(proj_type="cpp"):
        if proj_type == "cpp":
            return {
                "cxx_ver": "1z",
            }
        return {}

    return ["type"], ret


def __default_environment():
    return {
        "ubuntu_ver": {
            "default": "16.04",
            "desc": "Ubuntu version to use"
        },
        "compiler": {
            "default": "g++-7",
            "desc": "Compiler to use"
        },
        "cmake_min_ver": {
            "default": "3.5",
            "desc": "CMake minimum version"
        },
        "volume": {
            "default": "/root/app",
            "desc": "Where the volume will be mounted in the container"
        },
        "build_ppas": {
            "default": [],
            "desc": "Additional ppa repositories to add to build step"
        },
        "build_pckgs": {
            "default": [],
            "desc": "Additional packages to install for bulid step"
        },
        "ppas": {
            "default": [],
            "desc": "Additional ppa repositories to add to build and production"
        },
        "pckgs": {
            "default": [],
            "desc": "Additional packages to install to build and production"
        },
        "cmds": {
            "default": [],
            "desc": "Additional commands to run after packages are installed"
        },
        "prod_ppas": {
            "default": [],
            "desc": "Additional ppa repositories to add to production"
        },
        "prod_pckgs": {
            "default": [],
            "desc": "Additional packages to install to add to production"
        }
    }


def __default_app():
    return {
        "name": {
            "default": "myapp",
            "desc": "Name of project (executable is the same name)"
        },
        "type": {
            "default": "cpp",
            "desc": "Project type (cpp)"
        },
        "sources": {
            "default": ["main.cpp"],
            "desc": "Source files to compile"
        },
        "includes": {
            "default": [],
            "desc": "Include directories to add"
        },
        "dyn_libs": {
            "default": {},
            "desc": "Dynamic libraries to link to"
        },
        "stat_libs": {
            "default": [],
            "desc": "Static libraries to link to"
        },
        "flags": {
            "default": CallableDefaultFlag(__default_build_flags),
            "desc": "List of flags to pass to the compiler"
        }
    }


def __default_test():
    return __default_app()


def __default_project():
    return {
        "name": {
            "description": "The name of the project " +
                           "(should be unique to avoid container conflicts)"
        },
        "main": {
            "descrption": "The name of the application to run in production "
        }
    }


def __recursive_dict_merge(converted_dict, dict_input):
    default, required = converted_dict
    if isinstance(default, dict):
        new_dict = default.copy()
    else:
        new_dict = {}

    for k in dict_input.keys():
        if k not in new_dict:
            new_dict[k] = dict_input[k]
        else:
            v = dict_input[k]
            if isinstance(v, dict):
                new_dict[k] = __recursive_dict_merge(
                    (new_dict[k], ()),
                    dict_input[k]
                )
            else:
                new_dict[k] = v

    if isinstance(default, dict):
        for k in default.keys():
            if k not in dict_input and \
                    isinstance(new_dict[k], CallableDefaultFlag):
                callable_default = new_dict[k]
                params = callable_default.params
                params = [new_dict[k1] for k1 in params]
                new_dict[k] = callable_default(*params)

    for req in required:
        if req not in new_dict:
            raise Exception("Unprovided field %s!" % req)

    return new_dict


def __convert_to_default_dict(func):
    dictionary = func()
    required = []
    for k in dictionary.keys():
        if "default" in dictionary[k]:
            dictionary[k] = dictionary[k]["default"]
        else:
            required.append(k)

    return dictionary, required


def __merge(meta_func, provided):
    return __recursive_dict_merge(
        __convert_to_default_dict(
            meta_func
        ),
        provided
    )


def __app(provided):
    return __merge(__default_app, provided)


def __test(provided):
    return __merge(__default_test, provided)


def __environment(provided):
    return __merge(__default_environment, provided)


def __project(provided):
    return __merge(__default_project, provided)


def __append_dict(orig, new):
    for k in new.keys():
        if k not in orig:
            orig[k] = new[k]


def make_proj_config(yaml):
    if 'apps' not in yaml:
        raise Exception("No apps provided!")
    if 'tests' not in yaml:
        print "Warning! No tests are provided"
        yaml['tests'] = []
    if 'environment' not in yaml:
        yaml['environment'] = {}
    if 'project' not in yaml:
        raise Exception("You must provide a project section in proj.yaml!")
    if 'name' not in yaml['project']:
        raise Exception("You must provide a project name!")
    if 'main' not in yaml['project']:
        raise Exception("You must provide a main project app!")

    yaml['apps'] = [__app(app) for app in yaml['apps']]
    yaml['tests'] = [__test(test) for test in yaml['tests']]

    yaml['environment'] = __environment(yaml['environment'])

    yaml['project']['volume'] = yaml['environment']['volume']

    yaml['environment']['timestamp'] = datetime.datetime.now().isoformat()

    docker_conf.make(yaml)
    bash_conf.make(yaml)
    cmake_conf.make(yaml)
