"""
DeploySite -d

A simple module that allows you to deploy site and run application in a virtualenv (for python)

It runs pre_scripts and post_scripts deployment

For website, it can deploy Python and PHP/HTML site by create the settings and config files necessary

For application it just execute the scripts

DeploySite uses Gunicorn/Supervisort/Gevent/Nginx to launch Python app
FOr PHP or HTML site, Apache/Nginx

For Python site, it uses Nginx as a proxy

Features:
    - Deploy Python/PHP/HTML site
    -

A simple module to deploy flask/Python, PHP/HTML sites


Virtualenv

** TESTED ON CENTOS AND WITH PYTHON 2.7

@Author: Mardix
@Copyright: 2015 Mardix
LICENSE: MIT

https://github.com/mardix/deploysite

Requirements:
    Nginx
    Apache
    Gunicorn
    Supervisor
    Gevent
    Virtualenvwrapper
"""

import os
import datetime
import subprocess
import multiprocessing
import socket
import random
import argparse
import shutil
try:
    import yaml
except ImportError as ex:
    print("PyYaml is missing. pip --install pyyaml")

__version__ = "0.6.2"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "DeploySite"

CWD = os.getcwd()
NGINX_DEFAULT_PORT = 80
APACHE_DEFAULT_PORT = 8080

GUNICORN_PORT_RANGE = [8000, 9000]  # Port range for gunicorn proxy
GUNICORN_DEFAULT_MAX_REQUESTS = 500
GUNICORN_DEFAULT_WORKER_CLASS = "gevent"

VIRTUALENV = None
VERBOSE = False
VIRTUALENV_DIRECTORY = "/root/.virtualenvs"
VIRTUALENV_DEFAULT_PACKAGES = ["gunicorn", "gevent"]
LOCAL_BIN = "/usr/local/bin"

DEPLOY_CONFIG = None
# ------------------------------------------------------------------------------
# TEMPLATES

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

# CONF FILE
NGINX_CONF_FILE_PATTERN = "/etc/nginx/conf.d/%s.conf"
APACHE_CONF_FILE_PATTERN = "/etc/nginx/conf.d/%s.conf"

# NGINX SSL
NGINX_SSL_TPL = """
# SSL
    if ($scheme = "http") {{
        return 301 https://{SERVER_NAME}$request_uri;
    }}

    listen 443 ssl;
    ssl_certificate {CERT};
    ssl_certificate_key {KEY};
    
    ssl_session_cache shared:SSL:1m;
    ssl_session_timeout  5m;
    ssl_ciphers  HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers   on;
"""

NGINX_WWW_TO_NON_WWW_TPL = """
# www to non-www for both http and https
server {{
    listen 80;
    listen 443;
    server_name www.{SERVER_NAME};
    return 301 $scheme://{SERVER_NAME}$request_uri;
}}
"""

# NGINX FOR APP
APP_NGINX_TPL = """
server {{
    listen {PORT};
    server_name {SERVER_NAME};

    {SSL_CONFIG}

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

%%NGINX_WWW_TO_NON_WWW%%

""".replace("%%NGINX_WWW_TO_NON_WWW%%", NGINX_WWW_TO_NON_WWW_TPL)

# NGINX FOR PHP/HTML APP
PHPHTML_NGINX_FRONTEND_TPL = """
server {{
    listen   80;
    {SSL_CONFIG}
    server_name {SERVER_NAME};
    root {DIRECTORY};
    index index.php index.html index.htm;
    location / {{
        try_files $uri $uri/ /index.php;
    }}
    location ~ \.php$ {{
        proxy_set_header X-Real-IP  $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
        proxy_pass http://127.0.0.1:8080;
     }}
     location ~ /\.ht {{
        deny all;
    }}
}}

%%NGINX_WWW_TO_NON_WWW%%

""".replace("%%NGINX_WWW_TO_NON_WWW%%", NGINX_WWW_TO_NON_WWW_TPL)

# APACHE BACKEND
PHPHTML_APACHE_BACKEND_TPL = """
NameVirtualHost *:8080
<VirtualHost *:8080>
    ServerName {SERVER_NAME}
    DocumentRoot {DIRECTORY}
    ErrorLog {LOGS_DIR}/error_{SERVER_NAME}.log
    CustomLog {LOGS_DIR}/access_{SERVER_NAME}.log combined
    <Directory {DIRECTORY}>
        Options -Indexes +IncludesNOEXEC +SymLinksIfOwnerMatch +ExecCGI
        Order allow,deny
        Allow from all
        AllowOverride All Options=ExecCGI,Includes,IncludesNOEXEC,Indexes,MultiViews,SymLinksIfOwnerMatch
    </Directory>
</VirtualHost>
"""

# POST RECEIVE HOOK
GIT_POST_RECEIVE_HOOK_TPL = """
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
"""

# ------------------------------------------------------------------------------

def run(cmd, verbose=True):
    """ Shortcut to subprocess.call """
    if verbose and VERBOSE:
        subprocess.call(cmd.strip(), shell=True)
    else:
        process = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        return process.communicate()[0]

def runvenv(command, virtualenv=None):
    """
    run with virtualenv with the help of .bashrc
    :params command:
    :params  virtualenv: The venv name
    """
    kwargs = dict()
    if not VERBOSE:
        kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if virtualenv:
        command = "workon %s; %s; deactivate" % (virtualenv, command)
    cmd = ["/bin/bash", "-i", "-c", command]
    process = subprocess.Popen(cmd, **kwargs)
    return process.communicate()[0]

def get_venv_bin(bin_program=None, virtualenv=None):
    """
    Get the bin path of a virtualenv program
    """
    bin = (VIRTUALENV_DIRECTORY + "/%s/bin") % virtualenv if virtualenv else LOCAL_BIN
    return (bin + "/%s") % bin_program if bin_program else bin 

def v_print(text):
    """
    Verbose print. Will print only if VERBOSE is ON
    """
    if VERBOSE:
        print(text)

def is_port_open(port, host="127.0.0.1"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.shutdown(2)
        return True
    except Exception as e:
        return False

def generate_random_port():
    while True:
        port = random.randrange(GUNICORN_PORT_RANGE[0], GUNICORN_PORT_RANGE[1])
        if not is_port_open(port):
            return port

def nginx_reload():
    run("service nginx reload")

def nginx_restart():
    run("service nginx stop")
    run("service nginx start")

def apache_reload():
    run("service httpd reload")

def apache_restart():
    run("service httpd stop")
    run("service httpd start")

def install_requirements(directory, virtualenv=None):
    requirements_file = directory + "/requirements.txt"
    if os.path.isfile(requirements_file):
        pip = get_venv_bin(bin_program="pip", virtualenv=virtualenv)
        runvenv("%s install -r %s" % (pip, requirements_file), virtualenv=virtualenv)

# VirtualenvWrapper
def virtualenv_setup(name, remake=False):
    if remake:
        virtualenv_remove(name)
    virtualenv_make(name)

def virtualenv_make(name):
    runvenv("mkvirtualenv %s" % name)
    pip = get_venv_bin(bin_program="pip", virtualenv=name)
    packages = " ".join([p for p in VIRTUALENV_DEFAULT_PACKAGES])
    runvenv("%s install %s" % (pip, packages), virtualenv=name)

def virtualenv_remove(name):
    runvenv("rmvirtualenv %s" % name)

# Supervisor
def supervisortctl(action, name):
    return run("%s %s %s" % (SUPERVISOR_CTL, action, name))

def supervisor_status(name):
    """
    Return the supervisor status
    """
    status = run("%s %s %s" % (SUPERVISOR_CTL, "status", name), verbose=False)
    if status:
        _status = ' '.join(status.split()).split(" ")
        if _status[0] == name:
            return _status[1]
    return None

def supervisor_start(name, command, directory="/", user="root", environment=None):
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
                                      environment=environment or ""))
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

# NGinx, Gunicorn, PHP/HTML
def create_nginx_ssl_config(ssl, directory, server_name):
    """
    :param ssl: Must be a dict of {cert:"", key:""}. Path are relative to directory
    """
    # Setup SSL. Must be a dict of {cert:"", key:""}. Path are relative to the working dir
    ssl_config = ""
    if isinstance(ssl, dict) and "cert" in ssl and "key" in ssl:
        ssl_cert = directory + "/" + ssl["cert"]
        ssl_key = directory + "/" + ssl["key"]
        ssl_config = NGINX_SSL_TPL.format(CERT=ssl_cert,
                                          KEY=ssl_key,
                                          SERVER_NAME=server_name)
    return ssl_config

def gunicorn(app, server_name, directory=None, static_dir="static", ssl=None,
             virtualenv=None, remove=False, **config):
    """
    :params app:
    :params server_name:
    :params directory:
    :params static_dir:
    :params ssl: dict of {cert:"", key:""}
    :params remove: bool
    :params config: **dict gunicorn config
    """
    app_name = "gunicorn_%s" % (server_name.replace(".", "_"))
    nginx_conf = NGINX_CONF_FILE_PATTERN % server_name

    if remove:
        if os.path.isfile(nginx_conf):
            os.remove(nginx_conf)
        supervisor_stop(name=app_name, remove=True)
        reload_server()

    # Set workers
    if "workers" not in config:
        config["workers"] = (multiprocessing.cpu_count() * 2) + 1

    # Auto 'threads'
    if "threads" not in config:
        config["threads"] = 4

    # Auto 'max-requests', set to False to not set it
    if "max-requests" in config and config["max-request"] is False:
        del(config["max-requests"])
    elif "max-requests" not in config:
        config["max-requests"] = GUNICORN_DEFAULT_MAX_REQUESTS

    # Auto 'worker-class', set to False to not set it
    if "k" in config:
        config["worker-class"] = config["k"]
        del(config["k"])
    if "worker-class" in "config" and config["worker-class"] is False:
        del(config["worker-class"])
    elif "worker-class" not in config:
        config["worker-class"] = GUNICORN_DEFAULT_WORKER_CLASS

    if not directory:
        raise TypeError("'directory' path is missing")

    proxy_port = generate_random_port()

    port = NGINX_DEFAULT_PORT
    if "port" in config:
        port = config["port"]
        del(config["port"])

    settings = " ".join(["--%s %s" % (x[0], x[1]) for x in config.items()])
    gunicorn_bin = get_venv_bin(bin_program="gunicorn", virtualenv=virtualenv)
    command = "{GUNICORN_BIN} -b 0.0.0.0:{PROXY_PORT} {APP} {SETTINGS}"\
              .format(GUNICORN_BIN=gunicorn_bin,
                      PROXY_PORT=proxy_port,
                      APP=app, 
                      SETTINGS=settings,)

    supervisor_start(name=app_name,
                     command=command,
                     directory=directory)
    
    # NGINX Config file
    nginx_conf = NGINX_CONF_FILE_PATTERN % server_name
    with open(nginx_conf, "wb") as f:
        static_dir = directory + "/" + static_dir
        ssl_config = create_nginx_ssl_config(ssl=ssl,
                                             directory=directory,
                                             server_name=server_name)
        conf = APP_NGINX_TPL.format(PORT=port,
                                    PROXY_PORT=proxy_port,
                                    SERVER_NAME=server_name,
                                    STATIC_DIR=static_dir,
                                    SSL_CONFIG=ssl_config)        
        f.write(conf)    
    reload_server()

def phphtml_site(server_name, directory=None, remove=False, ssl=None):
    """
    To deploy PHP/HTML sites
    :param server_name: the server name
    :directory:
    :remove:
    :ssl: a dict of {cert:"", key:""}. Path are relative to the working dir
    """
    nginx_config_file = NGINX_CONF_FILE_PATTERN % server_name
    apache_config_file = APACHE_CONF_FILE_PATTERN % server_name

    if remove:
        if os.path.isfile(nginx_config_file):
            os.remove(nginx_config_file)
        if os.path.isfile(apache_config_file):
            os.remove(apache_config_file)
    else:
        logs_dir = "%s.logs" % directory

        if not os.path.isdir(logs_dir):
            os.makedirs(logs_dir)

        with open(apache_config_file, "wb") as f:
            f.write(PHPHTML_APACHE_BACKEND_TPL
                    .format(DIRECTORY=directory,
                            SERVER_NAME=server_name,
                            LOGS_DIR=logs_dir))

        with open(nginx_config_file, "wb") as f:
            ssl_config = create_nginx_ssl_config(ssl=ssl,
                                                 directory=directory,
                                                 server_name=server_name)
            f.write(PHPHTML_NGINX_FRONTEND_TPL
                    .format(DIRECTORY=directory,
                            SERVER_NAME=server_name,
                            LOGS_DIR=logs_dir,
                            SSL_CONFIG=ssl_config))
    reload_server()

# Deployment
def get_deploy_config(directory):
    """
    Return dict of the yaml file
    :params directory:
    """
    global DEPLOY_CONFIG

    if not DEPLOY_CONFIG:
        yaml_file = directory + "/deploy.yaml"
        if not os.path.isfile(yaml_file):
            raise Exception("Deploy file '%s' is required" % yaml_file)
        with open(yaml_file) as jfile:
            DEPLOY_CONFIG = yaml.load(jfile)
    return DEPLOY_CONFIG

def deploy_sites(directory):
    """
    To deploy sites
    :params directory:
    """
    conf_data = get_deploy_config(directory)
    virtualenv = conf_data["virtualenv"] if "virtualenv" in conf_data else None
    if "sites" in conf_data:
        for site in conf_data["sites"]:
            if "name" not in site:
                raise TypeError("'name' is missing in sites config")

            # Common config
            ssl = None
            if "ssl" in site:
                ssl = site["ssl"]
            server_name = site["name"]
            remove = True if "remove" in site and site["remove"] is True else False
            # PYTHON app
            if "application" in site:
                if not virtualenv:
                    raise TypeError("'virtualenv' in required to deploy Python application")

                application = site["application"]
                static_dir = site["static_dir"] if "static_dir" in site else "static"
                gunicorn_option = site["gunicorn"] if "gunicorn" in site else {}
                gunicorn(app=application,
                         server_name=server_name,
                         directory=directory,
                         static_dir=static_dir,
                         remove=remove,
                         ssl=ssl,
                         virtualenv=virtualenv,
                         **gunicorn_option)
            # PHP/HTML app
            else:
                phphtml_site(server_name=server_name,
                             directory=directory,
                             remove=remove,
                             ssl=ssl)
    else:
        raise TypeError("'sites' is missing in deploy.yaml")

def run_scripts(directory, script_type="pre"):
    """
    To run a scripts in a virtual env settings
    :params directory:
    """
    conf_data = get_deploy_config(directory)
    virtualenv = conf_data["virtualenv"] if "virtualenv" in conf_data else None
    script_key = "%s_scripts" % script_type
    if script_key in conf_data:
        for script in conf_data[script_key]:
            if "command" not in script:
                raise TypeError("'command' is missing in scripts")
            
            _dir = directory if "directory" not in script else script["directory"]
            command = script["command"]

            # You can use $ENV_PY and $ENV_BIN_DIR to refer to the virtualenv python
            # and the bin directory respectively
            command = command.replace("$ENV_PY", get_venv_bin(bin_program="python", virtualenv=virtualenv))
            command = command.replace("$ENV_BIN_DIR", get_venv_bin(virtualenv=virtualenv))

            # Worker script, run by supervisor
            if "worker" in script:
                if "name" not in script["worker"]:
                    raise TypeError("'name' is missing in worker script")
                name = script["worker"]["name"]
                user = "root" if "user" not in script["worker"] else script["worker"]["user"]
                if "remove" in script and script["remove"] is True:
                    supervisor_stop(name=name, remove=True)
                else:
                    supervisor_start(name=name,
                                     command=command,
                                     directory=_dir,
                                     user=user)            
            else:
                runvenv("cd %s; %s" % (_dir, command), virtualenv=virtualenv)

# Git
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

    It will create three dire
    cwd
        > /logs
        > /$repo
        > /$repo.git
    """
    working_dir, bare_repo = get_git_repo(directory, repo)
    logs_dir = "%s.logs" % working_dir

    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)
    if not os.path.isdir(working_dir):
        os.makedirs(working_dir)
    if not os.path.isdir(bare_repo):
        os.makedirs(bare_repo)
        run("cd %s && git init --bare" % bare_repo)
        return True
    return False

def update_git_post_receive_hook(directory, repo, self_deploy=False):
    """
    Update the post receive hook
    :params directory: the directory
    :params repo: The name of the repo
    :params self_deploy: if true, it will self deploy by running deploysite -a
    :return string: the bare repo path
    """
    working_dir, bare_repo = get_git_repo(directory, repo)
    post_receice_hook_file = "%s/hooks/post-receive" % bare_repo
    post_receive_command = ""

    if self_deploy:
        post_receive_command = "deploysite -d"
    post_receive_hook_data = GIT_POST_RECEIVE_HOOK_TPL.format(
                        WORKING_DIR=working_dir,
                        POST_RECEIVE_COMMAND=post_receive_command)

    # Always make a backup of the post receive hook
    if os.path.isfile(post_receice_hook_file):
        ts = datetime.datetime.now().strftime("%s")
        backup_file = (post_receice_hook_file + "-bk-%s") % ts
        shutil.copyfile(post_receice_hook_file, backup_file)

    with open(post_receice_hook_file, "wb") as f:
        f.write(post_receive_hook_data)
    run("chmod +x %s " % post_receice_hook_file)

def reload_server():
    apache_reload()
    nginx_reload()
    supervisor_reload()

def cmd():
    try:
        global VIRTUALENV_DIRECTORY
        global VERBOSE

        parser = argparse.ArgumentParser(description="%s %s" % (__NAME__, __version__))
        parser.add_argument("-d", "--deploy-all", help="Deploy all sites and run all scripts", action="store_true")
        parser.add_argument("--scripts", help="Execute Pre/Post scripts", action="store_true")
        parser.add_argument("--reload-server", help="To reload the servers", action="store_true")
        parser.add_argument("-r", "--repo", help="The repo name [-r www --git-init --self-deploy]")
        parser.add_argument("--git-init", help="To setup git bare repo name in "
                                                 "the current directory to push "
                                                 "to [ie: -r www --git-init]", action="store_true")
        parser.add_argument("--git-push-deploy", help="On git push, to deploy instantly. set to 0 or N to disallow "
                                                      "[-r www --git-push-deploy Y|N]")
        parser.add_argument("--non-verbose", help="Verbose", action="store_true")

        arg = parser.parse_args()
        VERBOSE = False if arg.non_verbose else True

        v_print("*" * 80)
        v_print("%s %s" % (__NAME__, __version__))
        v_print("")

        # The repo name to perform git stuff on
        repo = arg.repo or None

        # Automatically setup environment and install requirement
        if arg.deploy_all or arg.scripts:
            virtualenv = None
            _config = get_deploy_config(CWD)
            if "virtualenv" in _config:
                if "virtualenv_directory" in _config:
                    VIRTUALENV_DIRECTORY = _config["virtualenv_directory"]

                virtualenv = _config["virtualenv"]
                rebuild_virtualenv = True if "virtualenv_rebuild" in _config \
                                             and _config["virtualenv_rebuild"] is True else False
                v_print("> SETUP VIRTUALENV: %s " % virtualenv)
                virtualenv_setup(virtualenv, rebuild_virtualenv)

            v_print("> Install requirements")
            install_requirements(CWD, virtualenv)
            v_print("Done!\n")

        if arg.deploy_all:
            try:
                v_print(":: DEPLOY SITES ::")
                v_print("")
                v_print("> Running PRE-SCRIPTS ...")
                run_scripts(CWD, "pre")
                v_print("")
                v_print("> Deploying SITES ... ")
                deploy_sites(CWD)
                v_print("")
                v_print("> Running POST-SCRIPTS ...")
                run_scripts(CWD, "post")
                v_print("")
            except Exception as ex:
                v_print("Error: %s" % ex.__repr__())
            v_print("Done!\n")

        elif arg.scripts:
            try:
                v_print("> Running PRE-SCRIPTS ...")
                run_scripts(CWD, "pre")
                v_print("> Running POST-SCRIPTS ...")
                run_scripts(CWD, "post")
            except Exception as ex:
                v_print("Error: %s" % ex.__repr__())
            v_print("Done!\n")

        # Reload server
        if arg.reload_server:
            v_print("> Reloading server ...")
            reload_server()
            v_print("Done!\n")

        # Setup new repo
        if arg.git_init:
            v_print("> Create Git Bare repo ...")
            if not repo:
                raise TypeError("Missing 'repo' name")
            bare_repo = "%s/%s.git" % (CWD, repo)
            v_print("Repo: %s" % bare_repo)
            if git_init_bare_repo(CWD, repo):
                update_git_post_receive_hook(CWD, repo, False)
            v_print("Done!\n")

        # Git push deploy
        if arg.git_push_deploy:
            v_print("> Git Push Deploy ...")
            if not repo:
                raise TypeError("Missing 'repo' name")
            deploy = True if arg.git_push_deploy in [True, 1, "1", "y", "Y"] else False
            update_git_post_receive_hook(CWD, repo, deploy)
            v_print("Done!\n")

    except Exception as ex:
        v_print("ERROR: %s " % ex.__repr__())
