# DeploySite

A simple module to deploy flask application using Gunicorn, Supervisor and NGinx as a proxy

By default, application will be deployed on port 80 with Nginx.

**DeploySite** assign a random proxy for Gunicorn to work

Each application must have its own server name.

It also run scripts on the server and supervisor runners

### Install

	pip install deploysite


### How to use:

##Deploy WebApps

Create a file in your application root directory called: `deploy.yaml`

Add the following config in there:

    ---
      sites:
        -
          app_type: "PYTHON"
          server_name: "myserver.com"
          application: "run_myserver:flask_app"
          static_dir: "myserver/static"


Substitute `myserver.com` with your `site name`

Substitute `run_myserver:flask_app` with your flask app name

Substitute `myserver/static` with your application's static file

Then on the command line:

	deploysite --sites


#### Deploy multiple applications:

    ---
      sites:
        -
          app_type: "PYTHON"
          server_name: "myserver.com"
          application: "run_myserver:flask_app"
          static_dir: "myserver/static"
        -
          app_type: "PYTHON"
          server_name: "otherserver.com"
          application: "run_otherserver:flask_app"
          static_dir: "otherserver/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80
        -
          server_name: "worker.server.com"
          application: "run_worker_server:flask_app"
          static_dir: "worker_server/static"


This config above will deploy 3 apps.

For custom gunicorn configuration, set the gunicorn (dict) settings

---

##Run Scripts 

Add the following in your deploy.yaml to run scripts before the deployment of the app.

`scripts` is a **LIST** containing the full path of execution of your scripts

    scripts:
      - "hostname"
      - "ls -l"

So it could look something like this:

    ---
    scripts:
      - "hostname"
      - "ls -l"
      
To execute script alone:
	
	deploysite --scripts


## Runners

Runners are application to be run by supervisor

To execute script alone:

	deploysite --runners


## Deploy All

You can deploy and run everything at once:

	deploysite -a 
	
	or 
	
	deploysite --all
	
### Order of execution:

Upon launching `deploysite --all` , it will execute in the following order: 

0) Requirements

1) scripts

2) sites

3) Runners

---

## Other fun stuff

####Setup A Bare Git Repo

Setup a git repo, which will include a bare repo to push content to, and the actual content directory

    cd /home/mysite
    deploysite -r www --git-init


Will create the following:

    |
    |_ /home
        |
        |_ /mysite
            |
            |_ /www
            |
            |_ /www.git


`www.git` is a bare repo

`www` is where git will push the bare content to

#### To deploy on push

You set it to deploy on master push

    cd /home/mysite
    deploysite -r www --git-push-deploy 1


To not deploy on push

    cd /home/mysite
    deploysite -r www --git-push-deploy no

---

#### Reload Server

To reload the server

	deploysite --reload-server



####requirements.txt

If a requirements.txt exist, it will run it before deploying



---

### deploy.yaml:


Inside of the directory that contains the python web app, create a file `deploy.yaml`

**deploy.yaml** contains the params to properly deploy your app, run scripts etc

    ---
    # Sites: list of dict of web sites application
      sites:

    # Python app must have, must set app_type: PYTHON
        -
          app_type: "PYTHON"
          server_name: "myserver.com"
          application: "run_myserver:flask_app"
          static_dir: "myserver/static"

    # Python app with Gunicorn settings
        -
          app_type: "PYTHON"
          server_name: "otherserver.com"
          application: "run_otherserver:flask_app"
          static_dir: "otherserver/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80

    # To remove existing app. Set 'remove: True'
        -
          app_type: "PYTHON"
          server_name: "toremove.server.com"
          application: "run_worker_server:flask_app"
          static_dir: "worker_server/static"
          remove: True

    # Add SSL, by settings ssl: {cert: "", key: ""}
        -
          app_type: "PYTHON"
          server_name: "myserver.com"
          application: "run_myserver:flask_app"
          static_dir: "myserver/static"
          ssl:
            cert: "ssl/site.crt"
            key: "ssl/site.key"

    # PHP or HTML site, set app_type: PHP
        -
          app_type: "PHP"
          server_name: "myphpserver.com"

    #
    # Scripts: list of scripts to execute
      scripts:
        - "hostname"
        - "ls -l"

    #
    # Runners: List of dict of supervisor scripts to run
      runners:
        -
          name: ""
          command: ""
          directory: ""
          user: ""
          environment: ""
          remove: False  # Bool
        -
          name: ""
          command: ""
          directory: ""
          user: ""
          environment: ""


#### Description


	sites: # A list of dict with the following params
	   - app_type: PHP|PYTHON - The application type
       - application string: $module_name:$variable_name. The application to load (PYTHON)
       - server_name string: The name of the server ie: mysite.com (REQUIRED ON ALL)
       - static_dir string: The static directory relative to (PYTHON)
       - gunicorn: dict of gunicorn config (http://docs.gunicorn.org/en/develop/configure.html) (OPTIONAL PYTHON)
            workers: 4  (If not provided, it will assign the workers)
            preload: ""
            port: 80 (If not provided, it will assign it to port 80)
            max-requests: 500

	scripts: # A list of scripts path to execute

	runners: # A list of dict to run supervisor scripts
	    - name : the name of the app
	    - command: The command
	    - directory : directory
	    - user: user
	    - environment:
	    - remove: bool. If true and the runner is active, it will remove it


### Note: The Gunicorn config is set with the following by default

    ---
      sites:
        -
          ...
          gunicorn:
              workers: 4
              preload: " "
              port: 80
              max-requests: 500
              worker-class: gevent


- To change a default Gunicorn config set the default one to the desired value

- To remove a default Gunicorn config set the default one to False


---

### Requirements

- Yaml

- NGinx

- Apache

- Supervisor
 
- Gunicorn

- Gevent

---

License: MIT - Copyright 2014/2015 Mardix

