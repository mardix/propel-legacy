"""
Propel

Propel is a package to deploy multiple Python sites/application in virtualenv.

It also allows you to deploy PHP/HTML applications, run scripts and run workers with Supervisor.

For Python application, it uses Virtualenv to isolate each application, Gunicorn+Gevent as the backend server,
Supervisor and Nginx.

For PHP/HTML sites, it just uses the path as it would in normal environment, and you must have php-fpm

Requirements:
    Nginx
    Gunicorn
    Supervisor
    Gevent
    Virtualenvwrapper
    php-fpm

@Author: Mardix
@Copyright: 2015 Mardix
@license: MIT

"""

import os
import sys
import datetime
import subprocess
import multiprocessing
import socket
import random
import argparse
import shutil
import platform
import getpass

try:
    import yaml
except ImportError as ex:
    print("PyYaml is missing. pip install pyyaml")
try:
    from jinja2 import Template
except ImportError as ex:
    print("Jinja2 is missing. pip install jinja2")

__version__ = "0.22.6"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "Propel"

PY_EXECUTABLE = sys.executable
PY_USER = getpass.getuser()
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

DEPLOY_CONFIG_FILE = "propel.yml"
DEPLOY_CONFIG = None

# Configuration per distribution
DIST_CONF = {
    "RHEL": {
        "NGINX_CONF_FILE": "/etc/nginx/conf.d/%s.conf",
        "APT_GET": "yum",
        "INSTALL_PROGRAMS": ["nginx", 'groupinstall "Development Tools"', "python-devel", "php-fpm"],
        "RELOAD_PROGRAMS": ["nginx", "php-fpm"],
        "SETUP_CMD": ["sudo supervisord", "sudo service nginx start", "sudo service php-fpm start"],
        "UPSTART_PROGRAMS": ["nginx", "supervisord", "php-fpm"],
        "UPSTART_CMD": "chkconfig %s on"      
    },
    "DEBIAN": {
        "NGINX_CONF_FILE": "/etc/nginx/sites-enabled/%s.conf",
        "APT_GET": "apt-get",
        "INSTALL_PROGRAMS": ["nginx", 'python-dev', "php5-fpm"],
        "RELOAD_PROGRAMS": ["nginx", "php5-fpm"],
        "SETUP_CMD": ["sudo supervisord", "sudo service nginx start", "sudo service php5-fpm start"],
        "UPSTART_PROGRAMS": ["nginx", "supervisord", "php5-fpm"],
        "UPSTART_CMD": "update-rc.d %s defaults"
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

    {% if LOGS_DIR %}
    access_log {{ LOGS_DIR }}/access_{{ SERVER_NAME }}.log;
    error_log {{ LOGS_DIR }}/error_{{ SERVER_NAME }}.log;
    {% endif %}

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


{% if MAINTENANCE["ACTIVE"] %}
    set $maintenance on;

    {% set maintenance_page = "maintenance.html" %}
    {% if MAINTENANCE["PAGE"] %}
        {% set maintenance_page =  MAINTENANCE["PAGE"] %}
    {% endif %}

    # allow ips
    {% if MAINTENANCE["ALLOW_IPS"] %}
        if ($remote_addr ~ ({{ MAINTENANCE["ALLOW_IPS"] | join("|") }})) {
            set $maintenance off;
        }
    {% endif %}

    if ($maintenance = on) {
        return 503;
    }

    error_page 503 @maintenance;
    location @maintenance {
        {% if not MAINTENANCE["PAGE"] %}
            root /var/propel;
        {% endif %}

         rewrite ^(.*)$ /{{ maintenance_page }} break;
    }
{% endif %}


{% if (not MAINTENANCE["ACTIVE"])  or (MAINTENANCE["ACTIVE"] and MAINTENANCE["ALLOW_IPS"]) %}
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

{% else %}

    location / {
        return 503;
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
        {{ COMMAND }}
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
    raise NotImplemented("Platform '%s' is not compatible with Propel" % dist_name)

def get_dist_config(key):
    """
    Return the
    """
    dist = get_dist()
    if dist in DIST_CONF:
        return DIST_CONF[dist].get(key)
    raise AttributeError("Dist config '%s' not found" % key)

def reload_services():
    for svc in get_dist_config("RELOAD_PROGRAMS"):
        run("sudo service %s reload" % svc)

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

def _parse_command(command, virtualenv=None, directory=None):
    command = command.replace("$PYTHON_ENV", get_venv_bin(bin_program="python", virtualenv=virtualenv))
    command = command.replace("$LOCAL_BIN", get_venv_bin(virtualenv=virtualenv))
    command = command.replace("$CWD", directory)
    return command

def reload_server():
    reload_services()
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

    def update_post_receive_hook(self, repo, command=""):
        working_dir, bare_repo = self.get_working_dir(repo)
        post_receice_hook_file = "%s/hooks/post-receive" % bare_repo

        # Always make a backup of the post receive hook
        if os.path.isfile(post_receice_hook_file):
            ts = datetime.datetime.now().strftime("%s")
            backup_file = (post_receice_hook_file + "-bk-%s") % ts
            shutil.copyfile(post_receice_hook_file, backup_file)

        with open(post_receice_hook_file, "wb") as f:
            content = Template(POST_RECEIVE_HOOK_CONFIG)\
                .render(WORKING_DIR=working_dir, COMMAND=command)
            f.write(content)
        run("chmod +x %s " % post_receice_hook_file)

class App(object):
    virtualenv = None
    directory = None
    deployed_info = []

    def __init__(self, directory):
        self.config = get_deploy_config(directory)
        self.directory = directory
        self.virtualenv = self.config["virtualenv"] if "virtualenv" in self.config else {}

    def deploy_web(self, undeploy=False, maintenance=False):
        """
        To deploy/undeploy web app/sites
        """

        # Maintenance
        _maintenance = {"active": False, "page": None, "allow_ips": []}
        if "maintenance" in self.config:
            _maintenance.update(self.config["maintenance"])
        elif maintenance:
            _maintenance.update({"active": True})

        if "web" in self.config:
            for site in self.config["web"]:
                if "name" not in site:
                    raise TypeError("'name' is missing in sites config")
                if "application" in site and not self.virtualenv.get("name"):
                    raise TypeError("'virtualenv' in required for web Python app")

                name = site.get("name")
                directory = self.directory
                nginx = site.get("nginx", {})
                gunicorn_option = site.get("gunicorn", {})
                application = site.get("application", None)
                environment = site.get("environment", None)
                user = site.get("user", "root")
                remove = site.get("remove", False)
                gunicorn_app_name = "gunicorn_%s" % (name.replace(".", "_"))
                nginx_config_file = get_domain_conf_file(name)
                proxy_port = None

                if remove or undeploy:
                    if os.path.isfile(nginx_config_file):
                        os.remove(nginx_config_file)
                    if application:
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

                    # Site not under maintenance,
                    # or is under maintenance but allow certain ips
                    #  we'll activate the site
                    if (not _maintenance["active"]) \
                            or (_maintenance["active"] and _maintenance["allow_ips"]):
                        command = "{GUNICORN_BIN} -b 0.0.0.0:{PROXY_PORT} {APP} {SETTINGS}"\
                                  .format(GUNICORN_BIN=gunicorn_bin,
                                          PROXY_PORT=proxy_port,
                                          APP=application,
                                          SETTINGS=settings,)

                        Supervisor.start(name=gunicorn_app_name,
                                         command=command,
                                         directory=directory,
                                         user=user,
                                         environment=environment)
                    else:
                        Supervisor.stop(name=gunicorn_app_name, remove=True)

                logs_dir = nginx.get("logs_dir", None)
                if not logs_dir:
                    logs_dir = "%s.logs" % self.directory
                    if not os.path.isdir(logs_dir):
                        os.makedirs(logs_dir)

                self.deployed_info.append((name, proxy_port, gunicorn_app_name))

                with open(nginx_config_file, "wb") as f:
                    context = dict(NAME=name,
                                   SERVER_NAME=nginx.get("server_name", name),
                                   DIRECTORY=directory,
                                   PROXY_PORT=proxy_port,
                                   PORT=nginx.get("port", NGINX_DEFAULT_PORT),
                                   ROOT_DIR=nginx.get("root_dir", ""),
                                   ALIASES=nginx.get("aliases", {}),
                                   FORCE_NON_WWW=nginx.get("force_non_www", True),
                                   FORCE_WWW=nginx.get("force_www", False),
                                   SERVER_DIRECTIVES=nginx.get("server_directives", ""),
                                   SSL_CERT=nginx.get("ssl_cert", ""),
                                   SSL_KEY=nginx.get("ssl_key", ""),
                                   SSL_DIRECTIVES=nginx.get("ssl_directives", ""),
                                   LOGS_DIR=logs_dir,
                                   MAINTENANCE={
                                       "ACTIVE": _maintenance.get("active", False),
                                       "PAGE": _maintenance.get("page", None),
                                       "ALLOW_IPS": _maintenance.get("allow_ips", [])}
                                   )
                    content = Template(NGINX_CONFIG).render(**context)
                    f.write(content)
            reload_server()
        else:
            raise TypeError("'web' is missing in propel.yml")

    def maintenance(self, is_on=True):
        """
        Will put all the sites under maintenance
        To maintenance off, just deploy_web
        """
        if not is_on:
            self.deploy_web()
        else:
            if "web" in self.config:
                for site in self.config["web"]:
                    if "name" not in site:
                        raise TypeError("'name' is missing in sites config")

                    name = site["name"]
                    nginx = site["nginx"] if "nginx" in site else {}
                    directory = self.directory
                    nginx_config_file = get_domain_conf_file(name)
                    maintenance = {"active": False, "page": None, "allow_ips": []}

                    with open(nginx_config_file, "wb") as f:
                        context = dict(NAME=name,
                                       SERVER_NAME=nginx.get("server_name", name),
                                       DIRECTORY=directory,
                                       PROXY_PORT=None,
                                       PORT=nginx.get("port", NGINX_DEFAULT_PORT),
                                       ROOT_DIR=nginx.get("root_dir", ""),
                                       ALIASES=nginx.get("aliases", {}),
                                       FORCE_NON_WWW=nginx.get("force_non_www", False),
                                       FORCE_WWW=nginx.get("force_www", False),
                                       SERVER_DIRECTIVES=nginx.get("server_directives", ""),
                                       SSL_CERT=nginx.get("ssl_cert", ""),
                                       SSL_KEY=nginx.get("ssl_key", ""),
                                       SSL_DIRECTIVES=nginx.get("ssl_directives", ""),
                                       MAINTENANCE={"ACTIVE": True,
                                                    "PAGE": maintenance.get("page", None),
                                                    "ALLOW_IPS": []}
                                       )
                        content = Template(NGINX_CONFIG).render(**context)
                        f.write(content)
                reload_services()
            else:
                raise TypeError("'web' is missing in propel.yml")

    def run_scripts(self, name):
        """
        Run a one time script
        :params script_name: (string) The script name to run.
        """
        if "scripts" in self.config and name in self.config["scripts"]:
            for script in self.config["scripts"][name]:
                if "command" not in script:
                    raise TypeError("'command' is missing in scripts")

                # Exclude from running
                exclude = True if "exclude" in script and script["exclude"] is True else False
                if exclude:
                    continue

                directory = script["directory"] if "directory" in script else self.directory
                command = _parse_command(command=script["command"],
                                         virtualenv=self.virtualenv.get("name"),
                                         directory=directory)
                runvenv("cd %s; %s" % (directory, command), virtualenv=self.virtualenv.get("name"))

    def run_workers(self, undeploy=False):
        if "workers" in self.config:
            for worker in self.config["workers"]:
                if "name" not in worker:
                    raise TypeError("'name' is missing in workers")
                if "command" not in worker:
                    raise TypeError("'command' is missing in workers")

                name = worker.get("name")
                user = worker.get("user", "root")
                environment = worker.get("environment", "")
                directory = worker.get("directory", self.directory)
                command = _parse_command(command=worker["command"],
                                         virtualenv=self.virtualenv.get("name"),
                                         directory=directory)
                remove = worker.get("remove", False)
                exclude = worker.get("exclude", False)

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
            if self.virtualenv.get("rebuild") == True:
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
        parser.add_argument("-s", "--scripts", help="Run script by specifying name:"
                                                    " ie: [-s pre_web post_web other_one]", nargs='*')
        parser.add_argument("-k", "--workers", help="Run Workers", action="store_true")
        parser.add_argument("--reload-server", help="To reload the servers", action="store_true")

        parser.add_argument("-x", "--undeploy", help="To UNDEPLOY the application", action="store_true")
        parser.add_argument("-m", "--maintenance", help="Values: on|off - To set the site on maintenance. ie [--maintenance on]")

        parser.add_argument("--git-init", help="Setup a git bare repo $name to push content to. [--git-init $name]")
        parser.add_argument("--git-push-web", help="Set propel to deploy automatically when "
                                                   "push to the bare repo. [--git-push-web $name]")
        parser.add_argument("--git-push-cmd", help="Setup Command to execute after git push. Put cmds within quotes"
                                                   "ie: [--git-push-cmd $name 'ls  -l' 'cd ']", nargs='*')
        parser.add_argument("--silent", help="Disable verbosity", action="store_true")

        arg = parser.parse_args()
        VERBOSE = False if arg.silent else True

        _print("*" * 80)
        _print("%s %s" % (__NAME__, __version__))
        _print("")

        # Supervisor test
        if not os.path.isdir(SUPERVISOR_CONF_DIR):
            print("PROPEL has not been setup yet.")
            print("Run propel-setup")
            print("")
            exit()

        git = Git(CWD)
        app = None

        # Maintenance
        if arg.maintenance:
            app = App(CWD)
            maintenance = arg.maintenance.upper()
            if maintenance == "ON":
                _print(":: MAINTENANCE PAGE ON ::")
                app.maintenance()
            elif maintenance == "OFF":
                _print(":: MAINTENANCE PAGE OFF ::")
                arg.websites = True

        # Undeploy
        if arg.undeploy:
            _print(":: UNDEPLOY ::")
            app = App(CWD)
            app.deploy_web(undeploy=True)
            app.run_workers(undeploy=True)
            app.run_scripts("undeploy")
            app.destroy_virtualenv()

        # Deploy: Websites, scripts, workers may require a virtualenv
        elif arg.websites or arg.scripts or arg.workers:
            app = App(CWD)

            # Auto maintenance before doing any web deployment
            if arg.websites:
                app.maintenance()

            # Virtualenv
            if app.virtualenv.get("name"):
                _print("> SETTING UP VIRTUALENV: %s ... " % app.virtualenv.get("name"))
                app.setup_virtualenv()

                if app.virtualenv.get("directory"):
                    VIRTUALENV_DIRECTORY = app.virtualenv.get("directory")

                _print("> INSTALLING REQUIREMENTS ...")
                app.install_requirements()

            # Web
            if arg.websites:
                _print(":: DEPLOY WEBSITES ::")

                _print("> Running script pre_web ...")
                app.run_scripts("pre_web")

                _print("> Deploying WEB ... ")
                app.deploy_web()

                _print("> Running script post_web ...")
                app.run_scripts("post_web")

            # Scripts
            if arg.scripts:
                _print(":: RUN SCRIPTS ::")
                for name in arg.scripts:
                    _print("> Scripts: %s ..." % name)
                    app.run_scripts(name)

            # Workers
            if arg.workers:
                _print(":: RUN WORKERS ::")
                app.run_workers()

        # Extra
        else:
            if arg.git_init:
                repo = arg.git_init
                bare_repo = "%s/%s.git" % (CWD, repo)
                _print("> Creating Git Bare repo: %s ..." % bare_repo )
                if git.init_bare_repo(repo):
                    git.update_post_receive_hook(repo, False)

            if arg.git_push_web:
                repo = arg.git_push_web
                cmd = "propel -w"
                _print("> Setting WEB auto deploy on git push ...")
                git.update_post_receive_hook(repo, cmd)

            if arg.git_push_cmd:
                repo = arg.git_push_cmd[0]
                cmds = "; ".join(arg.git_push_cmd[1:])
                _print("> Setting custom CMD on git push ...")
                git.update_post_receive_hook(repo, cmds)

            if arg.reload_server:
                _print("> Reloading server ...")
                reload_server()
        _print("Completed!")
        _print("")

        if app:
            _print("-" * 80)
            _print("* Propel Deployment Summary *")
            _print("")
            if app.virtualenv.get("name"):
                _print("- Virtualenv: %s" % app.virtualenv.get("name"))
            if arg.websites and app.deployed_info:
                for i in app.deployed_info:
                    _print("- Webapp: %s" % i[0])
                    _print("\t Gunicorn port: %s" % i[1])
                    _print("\t Supervisor process name: %s" % i[0])

    except Exception as ex:
        _print("Propel ERROR: %s " % ex.__repr__())

    _print("")


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

def setup_propel():
    """
    To setup necessary paths and commands
    """
    global VERBOSE

    VERBOSE = True

    _print("Setting up Propel ... \n\n")

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

    MAINTENANCE_PAGE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
    <title>Site Maintenance</title>
    <link href='//fonts.googleapis.com/css?family=Raleway:400,300,600' rel='stylesheet' type='text/css'>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
    <style type="text/css">
      body { font: 20px "Raleway", Helvetica, sans-serif; color: #666; text-align: center; padding-top: 150px;}
        h1 { font-size: 50px; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="row">
            <div class="col-md-12 maintenance">
                <h1>We'll be back soon!</h1>
                <div>
                   Sorry for the inconvenience but we're performing some maintenance at the moment. <br>
                    We'll be back online shortly. <br>
                    Thanks!
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    """

    _apt_get = get_dist_config("APT_GET")

    conf_file = "/etc/supervisord.conf"
    init_d = "/etc/init.d/supervisord"
    var_propel_dir = "/var/propel"
    maintenance_page = "%s/maintenance.html" % var_propel_dir

    if not os.path.isdir(SUPERVISOR_CONF_DIR):
        os.makedirs(SUPERVISOR_CONF_DIR)
    if not os.path.isdir(SUPERVISOR_LOG_DIR):
        os.makedirs(SUPERVISOR_LOG_DIR)
    if not os.path.isdir(var_propel_dir):
        os.makedirs(var_propel_dir)

    run("sudo %s -y update" % _apt_get)

    install_programs = get_dist_config("INSTALL_PROGRAMS")
    run("sudo %s -y install %s" % (_apt_get, " ".join(install_programs)))
    
    run("echo_supervisord_conf > %s" % conf_file)
    with open(conf_file, "a") as f:
        lines = "\n[include]\n"
        lines += "files = " + SUPERVISOR_CONF_DIR + "/*.conf\n"
        f.write(lines)

    with open(init_d, "wb") as f:
        f.write(INIT_FILE)
    run("chmod +x %s" % init_d)

    # Add the virtualenvwrapper in bashrc
    run("mkdir -p ~/.virtualenvs")
    grep_test = 'if grep -q "#PROPEL-VIRTUALENVWRAPPER-START" ~/.bashrc; then echo "yes"; else echo "no"; fi'
    bash_venv = 'echo "\n#PROPEL-VIRTUALENVWRAPPER-START\n' \
                'export VIRTUALENVWRAPPER_PYTHON={PY_EXECUTABLE}\n' \
                'export WORKON_HOME=~/.virtualenvs\n' \
                'source /usr/local/bin/virtualenvwrapper.sh\n' \
                '#PROPEL-VIRTUALENVWRAPPER-END\n' \
                '" >> ~/.bashrc && source ~/.bashrc'.format(PY_EXECUTABLE=PY_EXECUTABLE)
    if run(grep_test, False) != "yes":
        run(bash_venv)

    upstart_cmd = get_dist_config("UPSTART_CMD")
    for _ in get_dist_config("UPSTART_PROGRAMS"):
        run(upstart_cmd % _)

    for _ in get_dist_config("SETUP_CMD"):
        run(_)

    with open(maintenance_page, "wb") as f:
        f.write(MAINTENANCE_PAGE)

    print("\nPropel setup completed!")


