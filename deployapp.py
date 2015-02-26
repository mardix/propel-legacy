"""
Deployapp

Deployapp is a package to deploy multiple Python sites/application in virtualenv.

It also allows you to deploy PHP/HTML applications, run scripts and run workers with Supervisor.

For Python application it uses Virtualenv to isolate each application, Gunicorn+Gevent as the backend server,
Supervisor and Nginx.

For PHP/HTML sites, it just uses the path as it would in normal environment, and you must have php-fpm

Requirements:
    Nginx
    Gunicorn
    Supervisor
    Gevent
    Virtualenvwrapper
    php-fpm

** TESTED ON CENTOS AND WITH PYTHON 2.7

@Author: Mardix
@Copyright: 2015 Mardix
@license: MIT

"""

import os
import datetime
import subprocess
import multiprocessing
import socket
import random
import argparse
import shutil
import platform
try:
    import yaml
except ImportError as ex:
    print("PyYaml is missing. pip --install pyyaml")
try:
    from jinja2 import Template
except ImportError as ex:
    print("Jinja2 is missing. pip --install jinja2")

__version__ = "0.10.1"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "Deployapp"

CWD = os.getcwd()

NGINX_DEFAULT_PORT = 80
GUNICORN_PORT_RANGE = [8000, 9000]  # Port range for gunicorn proxy
GUNICORN_DEFAULT_MAX_REQUESTS = 500
GUNICORN_DEFAULT_WORKER_CLASS = "gevent"

VIRTUALENV = None
VERBOSE = False
VIRTUALENV_DIRECTORY = "/root/.virtualenvs"
VIRTUALENV_DEFAULT_PACKAGES = ["gunicorn", "gevent"]
LOCAL_BIN = "/usr/local/bin"

DEPLOY_CONFIG_FILE = "deployapp.yml"
DEPLOY_CONFIG = None

# Configuration per distribution
DIST_CONF = {
    "RHEL": {
        "NGINX_CONF_FILE": "/etc/nginx/conf.d/%s.conf",
        "RESTART_NGINX": "service nginx restart",
        "RELOAD_NGINX": "service nginx reload"
    },
    "DEBIAN": {
        "NGINX_CONF_FILE": "/etc/nginx/sites-enabled/%s.conf",
        "RESTART_NGINX": "service nginx restart",
        "RELOAD_NGINX": "service nginx reload"
    }
}


# ------------------------------------------------------------------------------

# SUPERVISOR
SUPERVISOR_CTL = "/usr/local/bin/supervisorctl"
SUPERVISOR_LOG_DIR = "/var/log/supervisor"
SUPERVISOR_CONF_DIR = "/etc/supervisor"
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

NGINX_CONFIG = """
{%- macro SET_PATH(directory, path="") %}
    {%- if path and path.startswith('/') -%}
        {{ path }}
    {%- else -%}
        {{ directory }}/{{ path }}
    {%- endif -%}
{% endmacro -%}

server {

    listen {{ PORT }};
    server_name {{ SERVER_NAME }};
    root {{ SET_PATH(DIRECTORY, ROOT_DIR) }};
    access_log {{ LOGS_DIR }}/access_{{ SERVER_NAME }}.log;
    error_log {{ LOGS_DIR }}/error_{{ SERVER_NAME }}.log;

{%- if SSL_DIRECTIVES %}

    {{ SSL_DIRECTIVES }}

{%- elif SSL_CERT and SSL_KEY %}

    if ($scheme = "http") {
        return 301 https://{{ SERVER_NAME }}$request_uri;
    }

    listen 443 ssl;
    ssl_certificate     {{ SET_PATH(DIRECTORY, SSL_CERT) }} ;
    ssl_certificate_key {{ SET_PATH(DIRECTORY, SSL_KEY) }} ;

    ssl_session_cache shared:SSL:1m;
    ssl_session_timeout  5m;
    ssl_ciphers  HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers   on;

{% endif -%}

{% if PROXY_PORT %}
    location / {
        proxy_pass http://127.0.0.1:{{ PROXY_PORT }}/;
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

{% else %}

    location / {
        index index.html index.htm index.php;
    }

    # Pass PHP scripts to PHP-FPM
    location ~* \.php$ {
        fastcgi_index   index.php;
        fastcgi_pass    127.0.0.1:9000;
        include         fastcgi_params;
        fastcgi_param   SCRIPT_FILENAME    $document_root$fastcgi_script_name;
        fastcgi_param   SCRIPT_NAME        $fastcgi_script_name;
    }

{% endif %}

{%- if ALIASES %}
    {%- for alias, location in ALIASES.items() %}
    location {{ alias }} {
        alias {{ SET_PATH(DIRECTORY, location) }} ;
    }
    {% endfor -%}
{% endif -%}

    {{ SERVER_DIRECTIVES }}
}

{% if FORCE_NON_WWW or FORCE_WWW %}

server {
    listen {{ PORT }};

    {% if SSL_CERT and SSL_KEY %}
    listen 443 ssl;
    {% endif %}

    {% if FORCE_NON_WWW %}

        server_name www.{{ NAME }};
        return 301 $scheme://{{ NAME }}$request_uri;

    {% elif FORCE_WWW and not NAME.startswith('www.') %}

        server_name {{ NAME }};
        return 301 $scheme://www.{{ NAME }}$request_uri;

    {% endif %}
}

{% endif %}

"""

POST_RECEIVE_HOOK_CONFIG = """
#!/bin/sh
while read oldrev newrev refname
do
    branch=$(git rev-parse --symbolic --abbrev-ref $refname)
    if [ "master" == "$branch" ]; then
        GIT_WORK_TREE={{ WORKING_DIR }} git checkout -f
        cd {{ WORKING_DIR }}
        {% if SELF_DEPLOY_ON_PUSH %}
        deployapp -w
        {% endif %}
    fi
done
"""

# ------------------------------------------------------------------------------
def _print(text):
    """
    Verbose print. Will print only if VERBOSE is ON
    """
    if VERBOSE:
        print(text)

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

def get_dist_config(key):
    """
    Return the
    """
    dist = get_dist()
    if dist in DIST_CONF:
        return DIST_CONF[dist].get(key, None)
    return None

def get_dist():
    """
    Return the running distribution group
    RHEL: RHEL, CENTOS, FEDORA
    DEBIAN: UBUNTU, DEBIAN
    """
    dist_name = platform.linux_distribution()[0]
    system_name = platform.system()

    if dist_name.upper() in ["RHEL", "CENTOS", "FEDORA"]:
        return "RHEL"
    elif dist_name.upper() in ["DEBIAN", "UBUNTU"]:
        return "DEBIAN"
    elif not dist_name and system_name.upper() == "DARWIN":
        return "OSX"
    return None

def nginx_reload():
    run(get_dist_config("RELOAD_NGINX"))

def nginx_restart():
    run(get_dist_config("RESTART_NGINX"))

def get_domain_conf_file(domain):
    return get_dist_config("NGINX_CONF_FILE") % domain

# VirtualenvWrapper
def virtualenv_make(name):
    runvenv("mkvirtualenv %s" % name)
    pip = get_venv_bin(bin_program="pip", virtualenv=name)
    packages = " ".join([p for p in VIRTUALENV_DEFAULT_PACKAGES])
    runvenv("%s install %s" % (pip, packages), virtualenv=name)

def virtualenv_remove(name):
    runvenv("rmvirtualenv %s" % name)

# Deployment
def get_deploy_config(directory):
    """
    Return dict of the yaml file
    :params directory:
    """
    global DEPLOY_CONFIG

    if not DEPLOY_CONFIG:
        yaml_file = directory + "/" + DEPLOY_CONFIG_FILE
        if not os.path.isfile(yaml_file):
            raise Exception("Deploy file '%s' is required" % yaml_file)
        with open(yaml_file) as jfile:
            DEPLOY_CONFIG = yaml.load(jfile)
    return DEPLOY_CONFIG

def _parse_command(command, virtualenv=None):
    command = command.replace("$PYTHON", get_venv_bin(bin_program="python", virtualenv=virtualenv))
    command = command.replace("$LOCAL_BIN", get_venv_bin(virtualenv=virtualenv))
    return command

def reload_server():
    nginx_reload()
    Supervisor.reload()

class Supervisor(object):
    """
    Supervisor Class
    """

    @classmethod
    def ctl(cls, action, name):
        return run("%s %s %s" % (SUPERVISOR_CTL, action, name))

    @classmethod
    def status(cls, name):
        status = run("%s %s %s" % (SUPERVISOR_CTL, "status", name), verbose=False)
        if status:
            _status = ' '.join(status.split()).split(" ")
            if _status[0] == name:
                return _status[1]
        return None

    @classmethod
    def start(cls, name, command, directory="/", user="root", environment=None):
        """
        To Start/Set  a program with supervisor
        :params name: The name of the program
        :param command: The full command
        :param directory: The directory
        :param user:
        :param environment:
        """
        log_file = "%s/%s.log" % (SUPERVISOR_LOG_DIR, name)
        conf_file = "%s/%s.conf" % (SUPERVISOR_CONF_DIR, name)
        if cls.status(name) == "RUNNING":
            cls.ctl("stop", name)
        with open(conf_file, "wb") as f:
            f.write(SUPERVISOR_TPL.format(name=name,
                                          command=command,
                                          log=log_file,
                                          directory=directory,
                                          user=user,
                                          environment=environment or ""))
        cls.reload()
        cls.ctl("start", name)

    @classmethod
    def stop(cls, name, remove=True):
        """
        To Stop/Remove a program
        :params name: The name of the program
        :remove: If True will also delete the conf file
        """
        conf_file = "%s/%s.conf" % (SUPERVISOR_CONF_DIR, name)
        cls.ctl("stop", name)
        if remove:
            if os.path.isfile(conf_file):
                os.remove(conf_file)
            cls.ctl("remove", name)
        cls.reload()

    @classmethod
    def reload(cls):
        """
        Reload supervisor with the changes
        """
        cls.ctl("reread", "")
        cls.ctl("update", "")

class Git(object):
    def __init__(self, directory):
        self.directory = directory

    def get_working_dir(self, repo):
        working_dir = "%s/%s" % (self.directory, repo)
        bare_repo = "%s.git" % working_dir
        return working_dir, bare_repo

    def init_bare_repo(self, repo):
        working_dir, bare_repo = self.get_working_dir(repo)
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

    def update_post_receive_hook(self, repo, self_deploy=False):
        working_dir, bare_repo = self.get_working_dir(repo)
        post_receice_hook_file = "%s/hooks/post-receive" % bare_repo

        # Always make a backup of the post receive hook
        if os.path.isfile(post_receice_hook_file):
            ts = datetime.datetime.now().strftime("%s")
            backup_file = (post_receice_hook_file + "-bk-%s") % ts
            shutil.copyfile(post_receice_hook_file, backup_file)

        with open(post_receice_hook_file, "wb") as f:
            content = Template(POST_RECEIVE_HOOK_CONFIG)\
                .render(WORKING_DIR=working_dir, SELF_DEPLOY_ON_PUSH=self_deploy)
            f.write(content)
        run("chmod +x %s " % post_receice_hook_file)

class App(object):
    virtualenv = None
    directory = None

    def __init__(self, directory):
        self.config = get_deploy_config(directory)
        self.directory = directory
        self.virtualenv = self.config["virtualenv"] if "virtualenv" in self.config else {}

    def deploy_web(self, undeploy=False):
        """
        To deploy/undeploy web app/sites
        :params undeploy: bool - True to remove
        """
        if "web" in self.config:
            for site in self.config["web"]:
                if "name" not in site:
                    raise TypeError("'name' is missing in sites config")
                if "application" in site and not self.virtualenv.get("name"):
                    raise TypeError("'virtualenv' in required for web Python app")

                name = site["name"]
                nginx = site["nginx"] if "nginx" in site else {}
                gunicorn_option = site["gunicorn"] if "gunicorn" in site else {}
                application = site["application"] if "application" in site else None
                gunicorn_app_name = "gunicorn_%s" % (name.replace(".", "_"))
                proxy_port = None
                remove = True if "remove" in site and site["remove"] is True else False
                directory = self.directory
                nginx_config_file = get_domain_conf_file(name)
                exclude = True if "exclude" in site and site["exclude"] is True else False

                if undeploy:
                    remove = True
                    exclude = False

                if exclude:  # Exclude this site from deploy/re-deployment
                    continue

                if remove:
                    if os.path.isfile(nginx_config_file):
                        os.remove(nginx_config_file)
                    if "application" in site:
                        Supervisor.stop(name=gunicorn_app_name, remove=True)
                    continue

                # Python app will use Gunicorn+Gevent and Supervisor
                if application:
                    proxy_port = generate_random_port()
                    default_gunicorn = {
                        "workers": (multiprocessing.cpu_count() * 2) + 1,
                        "threads": 4,
                        "max-requests": GUNICORN_DEFAULT_MAX_REQUESTS,
                        "worker-class": GUNICORN_DEFAULT_WORKER_CLASS
                    }
                    gunicorn_option.update(default_gunicorn)

                    settings = " ".join(["--%s %s" % (x[0], x[1]) for x in gunicorn_option.items()])
                    gunicorn_bin = get_venv_bin(bin_program="gunicorn", virtualenv=self.virtualenv.get("name"))
                    command = "{GUNICORN_BIN} -b 0.0.0.0:{PROXY_PORT} {APP} {SETTINGS}"\
                              .format(GUNICORN_BIN=gunicorn_bin,
                                      PROXY_PORT=proxy_port,
                                      APP=application,
                                      SETTINGS=settings,)

                    Supervisor.start(name=gunicorn_app_name,
                                     command=command,
                                     directory=directory)

                logs_dir = nginx.get("logs_dir", None)
                if not logs_dir:
                    logs_dir = "%s.logs" % self.directory
                    if not os.path.isdir(logs_dir):
                        os.makedirs(logs_dir)

                with open(nginx_config_file, "wb") as f:
                    context = dict(NAME=name,
                                   SERVER_NAME=nginx.get("server_name", name),
                                   DIRECTORY=directory,
                                   PROXY_PORT=proxy_port,
                                   PORT=nginx.get("port", NGINX_DEFAULT_PORT),
                                   ROOT_DIR=nginx.get("root_dir", ""),
                                   ALIASES=nginx.get("aliases", {}),
                                   FORCE_NON_WWW=nginx.get("force_non_www", False),
                                   FORCE_WWW=nginx.get("force_www", False),
                                   SERVER_DIRECTIVES=nginx.get("server_directives", ""),
                                   SSL_CERT=nginx.get("ssl_cert", ""),
                                   SSL_KEY=nginx.get("ssl_key", ""),
                                   SSL_DIRECTIVES=nginx.get("ssl_directives", ""),
                                   LOGS_DIR=logs_dir
                                   )
                    content = Template(NGINX_CONFIG).render(**context)
                    f.write(content)
            reload_server()
        else:
            raise TypeError("'web' is missing in deployapp.yml")

    def run_scripts(self, script_name=None):
        """
        Run a one time script
        :params script_name: (string) The script name to run.
        """
        script_key = "scripts"
        if script_name:
            script_key = "scripts_%s" % script_name
        if script_key in self.config:
            for script in self.config[script_key]:
                if "command" not in script:
                    raise TypeError("'command' is missing in scripts")

                # Exclude from running
                exclude = True if "exclude" in script and script["exclude"] is True else False
                if exclude:
                    continue

                directory = script["directory"] if "directory" in script else self.directory
                command = _parse_command(command=script["command"], virtualenv=self.virtualenv.get("name"))
                runvenv("cd %s; %s" % (directory, command), virtualenv=self.virtualenv.get("name"))

    def run_workers(self, undeploy=False):
        if "workers" in self.config:
            for worker in self.config["workers"]:
                if "name" not in worker:
                    raise TypeError("'name' is missing in workers")
                if "command" not in worker:
                    raise TypeError("'command' is missing in workers")

                name = worker["name"]
                user = worker["user"] if "user" in worker else "root"
                environment = worker["environment"] if "environment" in worker else ""
                directory = worker["directory"] if "directory" in worker else self.directory
                command = _parse_command(command=worker["command"], virtualenv=self.virtualenv.get("name"))
                remove = True if "remove" in worker and worker["remove"] is True else False
                exclude = True if "exclude" in worker and worker["exclude"] is True else False

                if undeploy:
                    remove = True
                    exclude = False

                if exclude:  # Exclude worker from running
                    continue

                if remove:
                    Supervisor.stop(name=name, remove=True)
                    continue

                Supervisor.start(name=name,
                                 command=command,
                                 directory=directory,
                                 user=user,
                                 environment=environment)

    def install_requirements(self):
        requirements_file = self.directory + "/requirements.txt"
        if os.path.isfile(requirements_file):
            pip = get_venv_bin(bin_program="pip", virtualenv=self.virtualenv.get("name"))
            runvenv("%s install -r %s" % (pip, requirements_file), virtualenv=self.virtualenv.get("name"))

    def setup_virtualenv(self):
        if self.virtualenv.get("name"):
            if self.virtualenv.get("rebuild") is True:
                self.destroy_virtualenv()
            virtualenv_make(self.virtualenv.get("name"))

    def destroy_virtualenv(self):
        if self.virtualenv.get("name"):
            virtualenv_remove(self.virtualenv.get("name"))


def cmd():
    try:
        global VIRTUALENV_DIRECTORY
        global VERBOSE

        parser = argparse.ArgumentParser(description="%s %s" % (__NAME__, __version__))
        parser.add_argument("-w", "--websites", help="Deploy all sites", action="store_true")
        parser.add_argument("--scripts", help="Execute Pre/Post scripts", action="store_true")
        parser.add_argument("--name", help="To execute a specific script by name [--scripts --name $myname]")
        parser.add_argument("--workers", help="Run Workers", action="store_true")
        parser.add_argument("--reload-server", help="To reload the servers", action="store_true")

        parser.add_argument("--undeploy", help="To UNDEPLOY the application", action="store_true")

        parser.add_argument("--git-init", help="Setup a bare repo git. [--git-init www]")
        parser.add_argument("--git-push-deploy", help="To auto deploy upon git push"
                                                      "[--git-push-deploy www]")
        parser.add_argument("--git-push-no-deploy", help="To not auto deploy upon git push"
                                                      "[--git-push-no-deploy www]")
        parser.add_argument("--non-verbose", help="Disable verbosity", action="store_true")

        arg = parser.parse_args()
        VERBOSE = False if arg.non_verbose else True

        _print("*" * 80)
        _print("%s %s" % (__NAME__, __version__))
        _print("")

        git = Git(CWD)

        # Websites, scripts, workers may require a virtualenv
        if arg.websites or arg.scripts or arg.workers:
            app = App(CWD)
            if app.virtualenv.get("name"):
                _print("> SETUP VIRTUALENV: %s " % app.virtualenv.get("name"))
                app.setup_virtualenv()

                if app.virtualenv.get("directory"):
                    VIRTUALENV_DIRECTORY = app.virtualenv.get("directory")

                _print("> INSTALL REQUIREMENTS")
                app.install_requirements()

            if arg.websites:
                _print(":: DEPLOY WEBSITES ::")

                _print("> Running PRE-SCRIPTS ...")
                app.run_scripts("pre_web")

                _print("> Deploying WEB ... ")
                app.deploy_web()

                _print("> Running POST-SCRIPTS ...")
                app.run_scripts("post_web")

            if arg.scripts:
                name = arg.name or None
                _print("> Running SCRIPTS ...")
                app.run_scripts(name)

            if arg.workers:
                _print("> Running WORKERS...")
                app.run_workers()

        elif arg.undeploy:
            _print(":: UNDEPLOY ::")
            app = App(CWD)
            app.deploy_web(undeploy=True)
            app.run_workers(undeploy=True)
            app.run_scripts("undeploy")
            app.destroy_virtualenv()

        else:
            if arg.git_init:
                repo = arg.git_init
                bare_repo = "%s/%s.git" % (CWD, repo)
                _print("> Create Git Bare repo: %s" % bare_repo )
                if git.init_bare_repo(repo):
                    git.update_post_receive_hook(repo, False)

            if arg.git_push_deploy:
                repo = arg.git_push_deploy
                _print("> Set Git Auto Deploy on Git Push")
                git.update_post_receive_hook(repo, True)

            if arg.git_push_no_deploy:
                repo = arg.git_push_no_deploy
                _print("> NO Git Auto Deploy on Git Push")
                git.update_post_receive_hook(repo, False)

            if arg.reload_server:
                _print("> Reloading server ...")
                reload_server()


    except Exception as ex:
        _print("ERROR: %s " % ex.__repr__())
    _print("Done!\n")
    
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

def setup_deployapp():
    """
    To setup necessary paths and commands
    """
    print("SETUP DEPLOYAPP ...")

    conf_file = "/etc/supervisord.conf"
    init_d = "/etc/init.d/supervisord"

    if not os.path.isdir(SUPERVISOR_CONF_DIR):
        os.makedirs(SUPERVISOR_CONF_DIR)
    if not os.path.isdir(SUPERVISOR_LOG_DIR):
        os.makedirs(SUPERVISOR_LOG_DIR)

    run("echo_supervisord_conf > %s" % conf_file)
    with open(conf_file, "a") as f:
        lines = "\n[include]\n"
        lines += "files = " + SUPERVISOR_CONF_DIR + "/*.conf\n"
        f.write(lines)

    INIT_FILE = """
#!/bin/sh
# /etc/rc.d/init.d/supervisord
# chkconfig: - 64 36
# description: Supervisor Server
# processname: supervisord

. /etc/rc.d/init.d/functions
prog="supervisord"
prefix="/usr/local"
exec_prefix="${prefix}"
prog_bin="${exec_prefix}/bin/supervisord"
PIDFILE="/var/run/$prog.pid"
start()
{
        echo -n $"Starting $prog: "
        daemon $prog_bin --pidfile $PIDFILE
        [ -f $PIDFILE ] && success $"$prog startup" || failure $"$prog startup"
        echo
}
stop()
{
        echo -n $"Shutting down $prog: "
        [ -f $PIDFILE ] && killproc $prog || success $"$prog shutdown"
        echo
}
case "$1" in
  start)
    start
  ;;
  stop)
    stop
  ;;
  status)
        status $prog
  ;;
  restart)
    stop
    start
  ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
  ;;
esac
"""
    with open(init_d, "wb") as f:
        f.write(INIT_FILE)
    run("chmod +x %s" % init_d)
    run("chkconfig supervisord on")
    print("Done!")
