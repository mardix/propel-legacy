#!/usr/local/bin/python2.7
"""
DeployApp

A module to deploy python web app (ie: flask) using Gunicorn and Supervisor on Nginx.
Celery is also added as a bonus, but you must 'pip install celery' fisrt

@Author: Mardix
@Copyright: 2014 Mardix
LICENSE: MIT

https://github.com/mardix/deploy-py

Requirements:
    Nginx
    Gunicorn
    Supervisor
    Celery (optional, must pip install celery)
"""

import os
import subprocess
import socket
import random
import json
import argparse


__version__ = "0.3"
__author__ = "Mardix"
__license__ = "MIT"
__NAME__ = "DeployApp"

PIP_CMD = "pip2.7"

# PORT range to create random port upon creation of new instance
PORT_RANGE = [8000, 9000]


def run(cmd, verbose=True):
    """ Shortcut to subprocess.call """
    if verbose:
        subprocess.call(cmd.strip(), shell=True)
    else:
        process = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        return process.communicate()[0]


def is_port_open(port, host="127.0.0.1"):
    """Check if a port is open"""
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
    service = "nginx"
    run("service %s reload" % service)


def nginx_restart():
    """
    Restart Nginx
    """
    service = "nginx"
    run("chkconfig httpd on")
    run("service httpd stop")

    run("chkconfig %s on" % service)
    run("service %s stop" % service)
    run("service %s start" % service)


def install_requirements(dir):
    requirements = dir + "/requirements.txt"
    if os.path.isfile(requirements):
        run(PIP_CMD + " install -r %s" % requirements)

class Supervisor(object):

    service_name = "supervisord"
    conf_dir = "/etc/supervisord"
    log_dir = "/var/log/supervisor"
    CTL = "/usr/local/bin/supervisorctl"
    group_file = "_groups.conf"

    name = None

    def __init__(self, name):
        self.name = name

    def create(self, command, directory,
                    autostart=True,
                    user="root",
                    environment=""):
        """
        To add a program
        :param command: The command to execute
        :param directory: directory to cwd to before exec
        :param autostart: To autostart
        :param user: The user
        :param environment: Set the environment settings
        """

        log = "%s/%s.log" % (self.log_dir, self.name)
        config = {
            "command": command,
            "directory": directory,
            "user": user,
            "autostart": "true" if autostart else "false",
            "autorestart": "true" if autostart else "false",
            "stopwaitsecs": 600,
            "startsecs": 10,
            "stdout_logfile": log,
            "stderr_logfile": log,
            "environment": environment
        }
        self._write_conf(config)
        return self

    def start(self):
        return self.ctl("restart")

    def stop(self):
        return self.ctl("stop")

    def restart(self):
        return self.ctl("restart")

    def delete(self):
        self.ctl("remove")
        conf = self.conf_dir + "/%s.conf" % self.name
        if os.path.isfile(conf):
            os.remove(conf)

    def get_status(self):
        result = self.ctl("status")
        cmd_res = ' '.join(result.split()).split(" ")
        if cmd_res[0] == self.name:
            return cmd_res[1]
        else:
            return None

    def exists(self):
        """
        Checks if a process exists
        """
        return True if self.get_status() else False

    def is_running(self):
        """
        Return TRUE a process is running
        """
        return True if self.get_status() == "RUNNING" else False


    def update(self, restart=None, autostart=None):
        conf = self._read_conf()
        if restart is not None:
            conf["restart"] = "true" if restart else "false"
        if autostart is not None:
            conf["autostart"] = "true" if autostart else "false"
        self._write_conf(conf)


    def _write_conf(self, config):
        """
        Write the config data to conf file
        :dict config:
        """
        with open(self.conf_dir + "/%s.conf" % self.name, "w+") as f:
            content = "[program:%s]\n" % self.name
            for k in config:
                content += "%s=%s\n" % (k, config[k])
            f.seek(0)
            f.write(content)
            f.truncate()
            self.reread()

    def _read_conf(self):
        """
        Return the conf file into a dict
        :returns dict:
        """
        data = {}
        f = self.conf_dir + "/%s.conf" % self.name
        if os.path.isfile(f):
            with open(f, "r+") as conf:
                for line in conf.readlines():
                    line = line.strip()
                    if line:
                        if "[program:%s]" % self.name in line:
                            continue
                        else:
                            k, v = line.split("=", 1)
                            data[k] = v
        return data

    def ctl(self, action):
        return run("%s %s %s" % (self.CTL, action, self.name))

    def add_to_group(self, group_name):
        groups = self._read_groups()
        if group_name in groups:
            if "programs" in groups[group_name]:
                programs = groups[group_name]["programs"]
                if self.name not in programs:
                    groups[group_name]["programs"].append(self.name)
        else:
            groups[group_name] = {
                "programs": [self.name]
            }
        self._write_groups(groups)

    def remove_from_group(self, group_name):
        groups = self._read_groups()
        if group_name in groups:
            if "programs" in groups[group_name]:
                programs = groups[group_name]["programs"]
                if self.name in programs:
                    groups[group_name]["programs"].remove(self.name)
        self._write_groups(groups)


    def _write_groups(self, data):
        if data and isinstance(data, dict):
            content = ""
            for group_name in data:
                content += "[group:%s]\n" % group_name
                for k in data[group_name]:
                    v = data[group_name][k]
                    if isinstance(v, list):
                        v = ",".join(set(v))
                    content += "%s=%s\n" % (k, v)
                content += "\n"
            if content:
                with open(self.conf_dir + "/%s" % self.group_file, "w+") as f:
                    f.seek(0)
                    f.write(content)
                    f.truncate()
                    self.reread()

    @classmethod
    def _read_groups(cls):
        """
        Return the conf file into a dict
        :str name:
        :returns dict:
        """
        data = {}
        f = cls.conf_dir + "/%s" % cls.group_file
        group_name = None
        if os.path.isfile(f):
            with open(f, "r+") as conf:
                for line in conf.readlines():
                    line = line.strip()
                    if line:
                        if "[group:" in line:
                            group_name = line.replace("[", "").replace("]", "").split(":")[1]
                            data[group_name] = {}
                            continue
                        else:
                            if group_name:
                                k, v = line.split("=", 1)
                                if k == "programs":
                                    data[group_name]["programs"] = v.split(",")
                                else:
                                    data[group_name][k] = v
        return data

    @classmethod
    def reread(cls):
        run("%s reread" % cls.CTL)
        run("%s update" % cls.CTL)


class SupervisorMixin(object):

    supervisor = None

    def __init__(self, name):
        self._s_name = name
        self.supervisor = Supervisor(self.format_name(name))

    def supervise(self):
        pass

    @classmethod
    def format_name(cls, name):
        _name = name.replace(":", "_").replace(".", "_")
        return "%s__%s" % (cls.__name__.lower(), _name)


class Gunicorn(SupervisorMixin):
    service_name = "gunicorn"

    DEFAULT_PORT = 80
    DEFAULT_WORKERS = 4
    DEFAULT_STATIC_DIR = "static"

    conf = None
    directory = None

    def __init__(self, conf, directory=None):
        self.conf = conf
        self.directory = directory

        if "server_name" not in conf:
            raise TypeError("'server_name' is required")
        server_name = self.conf["server_name"]

        super(self.__class__, self).__init__(server_name)

    def deploy(self):

        if "app" not in self.conf:
            raise TypeError("'app' is required")
        if not self.directory:
            raise TypeError("'directory' is required")

        app = self.conf["app"]
        server_name = self.conf["server_name"]
        port = self.DEFAULT_PORT if "port" not in self.conf else self.conf["port"]
        workers = self.DEFAULT_WORKERS if "gunicorn_workers" not in self.conf else self.conf["gunicorn_workers"]
        static_dir = self.DEFAULT_STATIC_DIR if "static_dir" not in self.conf else self.conf["static_dir"]
        static_dir = self.directory + "/" + static_dir
        proxy_port = generate_random_port()

        self.create_nginx_conf_file(server_name, port, proxy_port, static_dir)

        command = "/usr/local/bin/gunicorn "\
                  "-w {WORKERS} " \
                  "-b 0.0.0.0:{PROXY_PORT} {APP}"\
                .format(WORKERS=workers,
                        PROXY_PORT=proxy_port,
                        APP=app)
        self.supervisor.create(command=command, directory=self.directory)
        self.reload()
        nginx_reload()


    def undeploy(self):

        server_name = self.conf["server_name"]

        conf_file = self.get_nginx_conf(server_name)
        if os.path.isfile(conf_file):
            os.remove(conf_file)

        self.supervisor.delete()
        self.reload()
        nginx_reload()


    @staticmethod
    def get_nginx_conf(server_name):
        return "/etc/nginx/conf.d/%s_gunicorn.conf" % server_name

    @classmethod
    def create_nginx_conf_file(cls, server_name, port, proxy_port, static_dir=""):
        conf_file = cls.get_nginx_conf(server_name)

        nginx_conf_tpl = """
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
        """.format(PORT=port,
                   PROXY_PORT=proxy_port,
                   SERVER_NAME=server_name,
                   STATIC_DIR=static_dir)

        if os.path.isfile(conf_file):
            os.remove(conf_file)
        with open(conf_file, "w+") as file:
            file.seek(0)
            file.write(nginx_conf_tpl)
            file.truncate()

    def reload(self):
        self.supervisor.restart()


class Celery(SupervisorMixin):
    service_name = "celery"

    directory = None
    app = None

    def __init__(self, app, directory=None):
        super(self.__class__, self.__class__).__init__(app)
        self.app = app
        self.directory = directory

    def supervise(self):
        if not self.directory:
            raise Exception()
        command = '/usr/local/bin/celery worker --app=%s -l INFO' % self.app
        self.supervisor.create(command=command, directory=self.directory)


class App(object):

    DEFAULT_PORT = 80

    path = None
    deploy_conf = None
    undeploy_conf = None

    def __init__(self, path):
        self.path = path

        deploy_file = self.path + "/deploy.json"
        if not os.path.isfile(deploy_file):
            raise Exception("Deploy file '%s' is required" % deploy_file)

        install_requirements(self.path)

        with open(deploy_file) as dfile:
            conf = json.load(dfile)
            if "deploy" in conf:
                self.deploy_conf = conf["deploy"]
            if "undeploy" in conf:
                self.undeploy_conf = conf["undeploy"]

        if self.deploy_conf:
            for app in self.deploy_conf:
                for ck in ["app", "server_name"]:
                    if ck not in app:
                        raise TypeError("'%s' is missing" % (ck, ))

        if self.undeploy_conf:
            for app in self.undeploy_conf:
                for ck in ["app", "server_name"]:
                    if ck not in app:
                        raise TypeError("'%s' is missing" % (ck, ))

    def deploy(self, app_name=None):
        """
        To deploy an app
        :param app_name string - optional, the application name without .py. ie: web.py -> web
        """
        deploy_conf = []
        if app_name:
            for _conf in self.deploy_conf:
                _app_name = _conf["app"].split(":")[0]
                if _app_name == app_name:
                    deploy_conf = [_conf]
                    break
        else:
            deploy_conf = self.deploy_conf

        for conf in deploy_conf:
            Gunicorn(conf, directory=self.path).deploy()

            if "celery" in conf and conf["celery"] is True:
                _app = conf["app"].split(":")[0]
                Celery(app=_app, directory=self.path).supervise()


    def undeploy(self, app_name=None):
        """
        To deploy an app
        :param app_name string - optional, the application name without .py. ie: web.py -> web
        """

        undeploy_conf = []
        if app_name:
            for _conf in self.undeploy_conf:
                _app_name = _conf["app"].split(":")[0]
                if _app_name == app_name:
                    undeploy_conf = [_conf]
                    break
        else:
            undeploy_conf = self.deploy_conf

        for conf in undeploy_conf:
            Gunicorn(conf).undeploy()

            if "celery" in conf and conf["celery"] is True:
                _app = conf["app"].split(":")[0]
                Celery(app=_app).supervisor.delete()


#-------------

CWD = os.getcwd()

def cmd():

    print ("")
    print ("-" * 80)
    print ("%s %s " % (__NAME__, __version__))
    print ("-" * 80)
    print("Current Location: %s" % CWD)
    print("")

    try:
        parser = argparse.ArgumentParser()

        parser.add_argument("-d", "--deploy", help="To deploy", action="store_true")
        parser.add_argument("-r", "--reload", help="To reload the server", action="store_true")
        parser.add_argument("--setup-repo", help="To setup git bare repo name in "
                                                 "the current directory to push "
                                                 "to [ie: --setup-repo www]")
        arg = parser.parse_args()

        # Deploy app
        if arg.deploy:
            print("> Initiating deployment ...")
            webapp = App(CWD)
            print("\t Undeploy ...")
            webapp.undeploy()
            print("\t Deploy ...")
            webapp.deploy()
            print("Done!\n")

        # Reload server
        if arg.reload:
            print ("> Reloading server ...")
            print("\t NGINX ...")
            nginx_reload()
            print("Done!\n")

        # Setup new repo
        if arg.setup_repo:
            name = arg.setup_repo

            print("> Setting up repo: %s ..." % name)

            working_dir = "%s/%s" % (CWD, name)
            bare_repo = "%s/%s.git" % (CWD, name)
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

            print("\tBare Repo: %s" % bare_repo)
            print("\tDeploy Dir: %s" % working_dir)
            print("Done!\n")

    except Exception as ex:
        print("EXCEPTION: %s " % ex.__str__())


