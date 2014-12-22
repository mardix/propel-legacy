"""
deployapp -a

A simple module to deploy flask application using NGINX, Gunicorn and Supervisor

It automatically set the Gunicorn server with a random port number, which is
then use in the NGINX as proxy.


@Author: Mardix
@Copyright: 2014 Mardix
LICENSE: MIT

https://github.com/mardix/deployapp

Requirements:
    Nginx
    Gunicorn
    Supervisor
"""

import os
import subprocess
import socket
import random
import argparse
try:
    import yaml
except ImportError as ex:
    print("PyYaml is missing. pip --install pyyaml")


__version__ = "0.11.0"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "DeployApp"

PIP_CMD = "pip2.7"
CWD = os.getcwd()

# PORT range to create random port upon creation of new instance
PORT_RANGE = [8000, 9000]

# SUPERVISOR
SUPERVISOR_CTL = "/usr/local/bin/supervisorctl"
SUPERVISOR_LOG_PATH = "/var/log/supervisor/%s.log"
SUPERVISOR_CONF_PATH = "/etc/supervisor/%s.conf"
SUPERVISOR_TPL = """
[program:{name}]
command={command}
directory={directory}
user={user}
autostart=true
autorestart=true
stopwaitsecs=600
startsecs=10
stdout_logfile={log}
stderr_logfile={log}
environment={environment}
"""

# GUNICORN
GUNICORN_NGINX_CONF_FILE_PATTERN = "/etc/nginx/conf.d/gunicorn_%s.conf"

# NGINX
NGNIX_PROXY_TPL = """
server
{{
listen {PORT};
server_name {SERVER_NAME};
location / {{
proxy_pass http://127.0.0.1:{PROXY_PORT}/;
proxy_redirect off;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Host $server_name;
}}
location /static {{
alias {STATIC_DIR};
}}
}}

"""

def run(cmd):
    """
    Shortcut to subprocess.call
    """
    subprocess.call(cmd.strip(), shell=True)


def is_port_open(port, host="127.0.0.1"):
    """
    Check if a port is open
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.shutdown(2)
        return True
    except Exception as e:
        return False


def generate_random_port():
    """
    Generate a random port to be used
    :returns int:
    """
    while True:
        port = random.randrange(PORT_RANGE[0], PORT_RANGE[1])
        if not is_port_open(port):
            return port


def nginx_reload():
    """
    Reload Nginx
    """
    run("service nginx reload")


def nginx_restart():
    """
    Restart Nginx
    """
    run("service nginx stop")
    run("service nginx start")


def install_requirements(directory):
    requirements = directory + "/requirements.txt"
    if os.path.isfile(requirements):
        run(PIP_CMD + " install -r %s" % requirements)


def supervisor_start(name, command, directory="/", user="root", environment=""):
    """
    To Start/Set  a program with supervisor
    :params name: The name of the program
    :param command: The full command
    :param directory: The directory
    :param user:
    :param environment:
    """
    log_file = SUPERVISOR_LOG_PATH % name
    conf_file = SUPERVISOR_CONF_PATH % name

    with open(conf_file, "wb") as f:
        f.write(SUPERVISOR_TPL.format(name=name,
                           command=command,
                           log=log_file,
                           directory=directory,
                           user=user,
                           environment=environment))
    supervisor_reload()
    run((SUPERVISOR_CTL + " start %s") % name)

def supervisor_stop(name, remove=True):
    """
    To Stop/Remove a program
    :params name: The name of the program
    :remove: If True will also delete the conf file
    """
    conf_file = SUPERVISOR_CONF_PATH % name
    run((SUPERVISOR_CTL + " %s stop") % name)
    if remove:
        if os.path.isfile(conf_file):
            os.remove(conf_file)
        run((SUPERVISOR_CTL + " %s remove") % name)
    supervisor_reload()


def supervisor_reload():
    """
    Reload supervisor with the changes
    """
    run(SUPERVISOR_CTL + " reread")
    run(SUPERVISOR_CTL + " update")


def create_nginx_proxy(server_name, port=80, proxy_port=None, static_dir="static"):
    """
    Create NGINX PROXY config file
    :params server_name:
    :params port:
    :params proxy_port:
    :params static_dir:
    """
    nginx_conf = GUNICORN_NGINX_CONF_FILE_PATTERN % server_name

    conf = NGNIX_PROXY_TPL.format(PORT=port,
                                  PROXY_PORT=proxy_port,
                                  SERVER_NAME=server_name,
                                  STATIC_DIR=static_dir)
    with open(nginx_conf, "wb") as f:
        f.write(conf)


def gunicorn(app,
             server_name,
             directory=None,
             static_dir="static",
             workers=4,
             port=80,
             deploy=False):
    """
    :params app:
    :params server_name:
    :params directory:
    :params static_dir:
    :params workers:
    :params port:
    :params deploy:
    """

    app_name = "gunicorn_%s" % (server_name.replace(".", "_"))
    nginx_conf = GUNICORN_NGINX_CONF_FILE_PATTERN % server_name

    if deploy is False:
        if os.path.isfile(nginx_conf):
            os.remove(nginx_conf)
        supervisor_stop(name=app_name, remove=True)
        return True

    if not directory:
        raise TypeError("'directory' path is missing")

    proxy_port = generate_random_port()

    command = "/usr/local/bin/gunicorn "\
              "-w {WORKERS} " \
              "-b 0.0.0.0:{PROXY_PORT} {APP}"\
              .format(WORKERS=workers,
                      PROXY_PORT=proxy_port,
                      APP=app)
    static_dir = directory + "/" + static_dir
    create_nginx_proxy(server_name=server_name,
                       port=port,
                       proxy_port=proxy_port,
                       static_dir=static_dir)
    supervisor_start(name=app_name,
                     command=command,
                     directory=directory)
    nginx_reload()
    return True

def deploy_config(directory):
    """
    Return the json file
    :params directory:
    """
    json_file = directory + "/deployapp.yaml"
    if not os.path.isfile(json_file):
        raise Exception("Deploy file '%s' is required" % json_file)
    with open(json_file) as jfile:
        conf_data = yaml.load(jfile)
    return conf_data


def deploy_webapps(directory):
    """
    To deploy webapps
    :params directory:
    """
    conf_data = deploy_config(directory)
    if "webapps" in conf_data:
        for app in conf_data["webapps"]:
            if "app" in app and "server_name" in app:
                gunicorn(app=app["app"],
                         server_name=app["server_name"],
                         directory=directory,
                         static_dir=app["static_dir"] if "static_dir" in app else "static",
                         workers=app["workers"] if "workers" in app else 4,
                         port=app["port"] if "port" in app else 80,
                         deploy=False if "deploy" in app and not app["deploy"] else True)
            else:
                raise TypeError("Webapp is missing: 'server_name' or 'app' in deployapp.yaml")
    else:
        raise TypeError("'webapps' is missing in deployapp.yaml")


def run_scripts(directory):
    """
    To run a scripts
    :params directory:
    """
    conf_data = deploy_config(directory)
    if "scripts" in conf_data:
        for script in conf_data["scripts"]:
            run(script)

def deploy_runners(directory):
    """
    Runners are supervisor scripts
    :params directory:
    """
    conf_data = deploy_config(directory)
    if "runners" in conf_data:
        for runner in conf_data["runners"]:
            if "name" in runner and "command" in runner and "directory" in runner:
                if "remove" in runner and runner["remove"]:
                    supervisor_stop(name=runner["name"], remove=True)
                else:
                    supervisor_start(name=runner["name"],
                                     command=runner["command"],
                                     directory=runner["directory"],
                                     user="root" if "user" not in runner else runner["user"],
                                     environment="" if "environment" not in runner else runner["environment"])
            else:
                raise TypeError("RUNNER is missing: 'name' or 'command' or 'directory' in deployapp.yaml")


def git_init_bare_repo(directory, repo):
    """
    Git init bare repo
    :params directory:
    :params repo:
    :return string: the bare repo path
    """
    working_dir = "%s/%s" % (directory, repo)
    bare_repo = "%s/%s.git" % (directory, repo)
    post_receice_hook_file = "%s/hooks/post-receive" % bare_repo
    post_receive_hook_data = "#!/bin/sh\n"
    post_receive_hook_data += "GIT_WORK_TREE=%s git checkout -f\n" % working_dir

    if not os.path.isdir(working_dir):
        os.makedirs(working_dir)
    if not os.path.isdir(bare_repo):
        os.makedirs(bare_repo)
        _cmd = """
        cd %s
        git init --bare
        """ % bare_repo
        run(_cmd)

    if not os.path.isfile(post_receice_hook_file):
        with open(post_receice_hook_file, "w") as f:
            f.write(post_receive_hook_data)
        run("chmod +x %s " % post_receice_hook_file)
    return bare_repo

def cmd():

    print ("")
    print ("-" * 80)
    print ("%s %s " % (__NAME__, __version__))
    print ("-" * 80)
    print("Current Location: %s" % CWD)
    print("")

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-a", "--all", help="Deploy all sites and run all scripts", action="store_true")
        parser.add_argument("-w", "--webapps", help="To deploy the apps", action="store_true")
        parser.add_argument("--scripts", help="To execute scripts in the scripts list", action="store_true")
        parser.add_argument("--runners", help="Runners are scripts to run with Supervisor ", action="store_true")
        parser.add_argument("-r", "--reload", help="To reload the servers", action="store_true")
        parser.add_argument("--git-init", help="To setup git bare repo name in "
                                                 "the current directory to push "
                                                 "to [ie: --git-init www]")
        arg = parser.parse_args()

        if arg.all:
            arg.scripts = True
            arg.webapps = True
            arg.runners = True

        # Order of execution is important:
        #   - install_requirements
        #   - scripts
        #   - webapps
        #   - runners
        # -------------------

        # Automatically install requirement
        if arg.webapps or arg.scripts or arg.runners:
            install_requirements(CWD)

        # Run scripts
        if arg.scripts:
            print("> Running SCRIPTS ...")
            run_scripts(CWD)
            print("Done!\n")

        # Deploy app
        if arg.webapps:
            print("> Deploying WEBAPPS ... ")
            deploy_webapps(CWD)
            print("Done!\n")

        # Run runners
        if arg.runners:
            print("> Deploying RUNNERS ...")
            deploy_runners(CWD)
            print("Done!\n")

        # Reload server
        if arg.reload:
            print ("> Reloading server ...")
            print(">> NGINX ...")
            nginx_reload()
            print (">> Supervisor...")
            supervisor_reload()
            print("Done!\n")

        # Setup new repo
        if arg.git_init:
            repo = arg.git_init
            print("> Setup Git Repo '%s' @ %s ..." % (repo, CWD))
            bare_repo = git_init_bare_repo(CWD, repo)
            print("\tBare Repo: %s" % bare_repo)
            print("Done!\n")

    except Exception as ex:
        print("EXCEPTION: %s " % ex.__str__())
