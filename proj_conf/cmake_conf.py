import pystache


def __cmake_template():
    return """
cmake_minimum_required(VERSION {{environment.cmake_min_ver}})
enable_language(CXX)
set(CMAKE_THREAD_PREFER_PTHREAD TRUE)
FIND_PACKAGE ( Threads REQUIRED )

enable_testing()

{{#apps}}
project({{name}} CXX)
{{/apps}}
{{#tests}}
project(test_{{name}} CXX)
{{/tests}}

set(CMAKE_BINARY_DIR bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

configure_file(prod_tests.sh bin/prod_tests.sh COPYONLY)

{{#apps}}
set(SOURCE_FILES {{#sources}}{{.}} {{/sources}})
set(CMAKE_CXX_FLAGS "{{#other_flags}}{{.}} {{val}}{{/other_flags}}")
set(CMAKE_CXX_FLAGS "-std=c++{{flags.cxx_ver}} ${CMAKE_CXX_FLAGS}")
add_executable({{name}} ${SOURCE_FILES})

{{#includes}}
include_directories({{.}})
{{/includes}}

{{#static_libs}}
target_link_libraries({{app}} {{link}})
{{/static_libs}}

{{#dyn_libs}}
{{#find}}
find_package({{name}} REQUIRED)
include_directories({{include}})
target_link_libraries({{app}} {{link}})
{{/find}}
{{#link}}
target_link_libraries({{app}} {{.}})
{{/link}}
{{/dyn_libs}}

{{/apps}}
{{#tests}}
set(SOURCE_FILES {{#sources}}{{.}} {{/sources}})
set(CMAKE_CXX_FLAGS "{{#other_flags}}{{.}} {{val}}{{/other_flags}}")
set(CMAKE_CXX_FLAGS "-std=c++{{flags.cxx_ver}} ${CMAKE_CXX_FLAGS}")
add_executable(test_{{name}} ${SOURCE_FILES})
add_test({{name}} bin/test_{{name}})


{{#includes}}
include_directories({{.}})
{{/includes}}

{{#static_libs}}
target_link_libraries({{app}} {{link}})
{{/static_libs}}

{{#dyn_libs}}
{{#find}}
find_package({{name}} REQUIRED)
include_directories({{include}})
target_link_libraries({{app}} {{link}})
{{/find}}
{{#link}}
target_link_libraries({{app}} {{.}})
{{/link}}
{{/dyn_libs}}
{{/tests}}

"""


def make(yaml):
    with open("CMakeLists.txt", "w") as out_file:
        cmake_confs = ['apps', 'tests']
        for conf in cmake_confs:
            for app in yaml[conf]:
                app_name = app['name']
                if conf == 'tests':
                    app_name = 'test_' + app_name
                if 'dyn_libs' in app:
                    lib_types = app['dyn_libs']
                    app['dyn_libs']['app'] = app_name
                    if 'find' in lib_types:
                        for i in range(len(lib_types['find'])):
                            lib = lib_types['find'][i]
                            new_lib = lib.copy()
                            new_lib['cap'] = lib['name'].upper()
                            new_lib['app'] = app_name
                            if 'link' in lib:
                                new_lib['link'] = lib['link']
                            else:
                                new_lib['link'] = "${" + new_lib['cap'] + "_LIBRARIES}"
                            if 'include' in lib:
                                new_lib['include'] = lib['include']
                            else:
                                new_lib['include'] = "${" + new_lib['cap'] + "_INCLUDE_DIRS}"
                            lib_types['find'][i] = new_lib
                if 'static_libs' in app and 'link' in app['static_libs']:
                    links = app['static_libs']['link']
                    for index in range(len(links)):
                        new_lib = {
                            'name': links[index],
                            'app': app_name
                        }
                        links[index] = new_lib

        out_file.write(
            pystache.render(
                __cmake_template(),
                yaml
            )
            .replace('&#123;', '{')
        )
