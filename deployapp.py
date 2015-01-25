"""
deployapp -a

A simple module to deploy flask application using NGINX, Gunicorn, Supervisor and Gevent

It automatically set the Gunicorn server with a random port number, which is
then used in the NGINX as proxy.


@Author: Mardix
@Copyright: 2015 Mardix
LICENSE: MIT

https://github.com/mardix/deployapp

Requirements:
    Nginx
    Gunicorn
    Supervisor
"""

import os
import subprocess
import multiprocessing
import socket
import random
import argparse
try:
    import yaml
except ImportError as ex:
    print("PyYaml is missing. pip --install pyyaml")


__version__ = "0.22.0"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "DeployApp"

PIP_CMD = "pip2.7"
CWD = os.getcwd()
DEFAULT_PORT = 80
DEFAULT_MAX_REQUESTS = 500
DEFAULT_WORKER_CLASS = "gevent"

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
    process = subprocess.Popen(cmd, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.communicate()[0]


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

def supervisortctl(action, name):
    return run("%s %s %s" % (SUPERVISOR_CTL, action, name))

def supervisor_status(name):
    """
    Return the supervisor status
    """

    status = supervisortctl("status", name)
    if status:
        _status = ' '.join(status.split()).split(" ")
        if _status[0] == name:
            return _status[1]
    return None

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
    if supervisor_status(name) == "RUNNING":
        supervisortctl("stop", name)
    with open(conf_file, "wb") as f:
        f.write(SUPERVISOR_TPL.format(name=name,
                           command=command,
                           log=log_file,
                           directory=directory,
                           user=user,
                           environment=environment))
    supervisor_reload()
    supervisortctl("start", name)

def supervisor_stop(name, remove=True):
    """
    To Stop/Remove a program
    :params name: The name of the program
    :remove: If True will also delete the conf file
    """
    conf_file = SUPERVISOR_CONF_PATH % name
    supervisortctl("stop", name)
    if remove:
        if os.path.isfile(conf_file):
            os.remove(conf_file)
        supervisortctl("remove", name)
    supervisor_reload()


def supervisor_reload():
    """
    Reload supervisor with the changes
    """
    supervisortctl("reread", "")
    supervisortctl("update", "")


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


def gunicorn(app, server_name, directory=None, static_dir="static", **config):
    """
    :params app:
    :params server_name:
    :params directory:
    :params static_dir:
    :params config: **dict gunicorn config
    """

    app_name = "gunicorn_%s" % (server_name.replace(".", "_"))
    nginx_conf = GUNICORN_NGINX_CONF_FILE_PATTERN % server_name

    if "remove" in config and config["remove"] is True:
        if os.path.isfile(nginx_conf):
            os.remove(nginx_conf)
        supervisor_stop(name=app_name, remove=True)
        return True

    if "workers" not in config:
        config["workers"] = (multiprocessing.cpu_count() * 2) + 1

    # Auto 'max-requests', set to False to not set it
    if "max-requests" in config and config["max-request"] is False:
        del(config["max-requests"])
    elif "max-requests" not in config:
        config["max-requests"] = DEFAULT_MAX_REQUESTS

    # Auto 'preload', set to False to not set it
    if "preload" in "config" and config["preload"] is False:
        del(config["preload"])
    elif "preload" not in config:
        config["preload"] = " "

    # Auto 'worker-class', set to False to not set it
    if "k" in config:
        config["worker-class"] = config["k"]
        del(config["k"])
    if "worker-class" in "config" and config["worker-class"] is False:
        del(config["worker-class"])
    elif "worker-class" not in config:
        config["worker-class"] = DEFAULT_WORKER_CLASS

    if not directory:
        raise TypeError("'directory' path is missing")

    proxy_port = generate_random_port()

    port = DEFAULT_PORT
    if "port" in config:
        port = config["port"]
        del(config["port"])

    settings = " ".join(["--%s %s" % (x[0], x[1]) for x in config.items()])
    command = "/usr/local/bin/gunicorn "\
              "-b 0.0.0.0:{PROXY_PORT} {APP}"\
              " {SETTINGS}"\
              .format(SETTINGS=settings,
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
    Return the yaml file
    :params directory:
    """
    yaml_file = directory + "/deployapp.yaml"
    if not os.path.isfile(yaml_file):
        raise Exception("Deploy file '%s' is required" % yaml_file)
    with open(yaml_file) as jfile:
        conf_data = yaml.load(jfile)
    return conf_data

def deploy_sites(directory):
    """
    To deploy sites
    :params directory:
    """
    conf_data = deploy_config(directory)
    if "sites" in conf_data:
        for app in conf_data["sites"]:
            if "app" in app and "server_name" in app:
                gunicorn_conf = {}
                if "gunicorn" in app:
                    gunicorn_conf = app["gunicorn"]
                gunicorn(app=app["app"],
                         server_name=app["server_name"],
                         directory=directory,
                         static_dir=app["static_dir"] if "static_dir" in app else "static",
                         **gunicorn_conf
                         )
            else:
                raise TypeError("sites is missing: 'server_name' or 'app' in deployapp.yaml")
    else:
        raise TypeError("'sites' is missing in deployapp.yaml")


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


def get_git_repo(directory, repo):
    working_dir = "%s/%s" % (directory, repo)
    bare_repo = "%s.git" % working_dir
    return working_dir, bare_repo

def git_init_bare_repo(directory, repo):
    """
    Create a bare repo
    :params directory: the directory
    :params repo: The name of the repo
    :returns bool: True if created
    """
    working_dir, bare_repo = get_git_repo(directory, repo)
    if not os.path.isdir(working_dir):
        os.makedirs(working_dir)
    if not os.path.isdir(bare_repo):
        os.makedirs(bare_repo)
        run("cd %s && git init --bare" % bare_repo)
        return True
    return False

def update_git_post_receive_hook(directory, repo, self_deploy):
    """
    Update the post receive hook
    :params directory: the directory
    :params repo: The name of the repo
    :params self_deploy: if true, it will self deploy by running deployapp -a
    :return string: the bare repo path
    """

    working_dir, bare_repo = get_git_repo(directory, repo)
    post_receice_hook_file = "%s/hooks/post-receive" % bare_repo
    post_receive_command = ""

    if self_deploy:
        post_receive_command = "deployapp -a"

    post_receive_hook_data ="""
#!/bin/sh
while read oldrev newrev refname
do
    branch=$(git rev-parse --symbolic --abbrev-ref $refname)
    if [ "master" == "$branch" ]; then
        GIT_WORK_TREE={WORKING_DIR} git checkout -f
        cd {WORKING_DIR}
        {POST_RECEIVE_COMMAND}
    fi
done
""".format(WORKING_DIR=working_dir,
           POST_RECEIVE_COMMAND=post_receive_command)

    with open(post_receice_hook_file, "wb") as f:
        f.write(post_receive_hook_data)
    run("chmod +x %s " % post_receice_hook_file)


def cmd():
    try:
        parser = argparse.ArgumentParser(description="%s %s" % (__NAME__, __version__))
        parser.add_argument("-a", "--all", help="Deploy all sites and run all scripts", action="store_true")
        parser.add_argument("--sites", help="To deploy the apps", action="store_true")
        parser.add_argument("--scripts", help="To execute scripts in the scripts list", action="store_true")
        parser.add_argument("--runners", help="Runners are scripts to run with Supervisor ", action="store_true")
        parser.add_argument("--reload-server", help="To reload the servers", action="store_true")
        parser.add_argument("--repo")
        parser.add_argument("--git-init", help="To setup git bare repo name in "
                                                 "the current directory to push "
                                                 "to [ie: --git-init www]")
        parser.add_argument("--set-self-deploy", help="To set deployapp to run on git push "
                                                      "[--set-self-deploy www]")
        parser.add_argument("--unset-self-deploy", help="If deployapp was set to run on git push, it will disable it "
                                                        "[--unset-self-deploy www]")

        arg = parser.parse_args()

        if arg.all:
            arg.scripts = True
            arg.sites = True
            arg.runners = True

        # Order of execution is important:
        #   - install_requirements
        #   - scripts
        #   - sites
        #   - runners
        # -------------------

        # Automatically install requirement
        if arg.sites or arg.scripts or arg.runners:
            print("> INSTALL REQUIREMENTS ...")
            install_requirements(CWD)

        # Run scripts
        if arg.scripts:
            print("> Running SCRIPTS ...")
            run_scripts(CWD)
            print("Done!\n")

        # Deploy app
        if arg.sites:
            print("> Deploying SITES ... ")
            try:
                deploy_sites(CWD)
            except Exception as ex:
                print("Error: %s" % ex.message)
            print("Done!\n")

        # Run runners
        if arg.runners:
            print("> Deploying RUNNERS ...")
            deploy_runners(CWD)
            print("Done!\n")

        # Reload server
        if arg.reload_server:
            print ("> Reloading server ...")
            print(">> NGINX ...")
            nginx_reload()
            print (">> Supervisor...")
            supervisor_reload()
            print("Done!\n")

        # Setup new repo
        if arg.git_init:
            repo = arg.git_init
            bare_repo = "%s/%s.git" % (CWD, repo)
            print("> Setup Git Repo @ %s ..." % bare_repo)
            if git_init_bare_repo(CWD, repo):
                update_git_post_receive_hook(CWD, repo, False)
            print("\tBare Repo created @ %s" % bare_repo)
            print("Done!\n")

        # Set self deploy
        if arg.set_self_deploy:
            repo = arg.set_self_deploy
            print("> Setting self deploy...")
            update_git_post_receive_hook(CWD, repo, True)
            print("Done!\n")

        # Unset self deploy
        if arg.unset_self_deploy:
            repo = arg.unset_self_deploy
            print("> Unsetting self deploy...")
            update_git_post_receive_hook(CWD, repo, False)
            print("Done!\n")

    except Exception as ex:
        print("EXCEPTION: %s " % ex.__str__())
