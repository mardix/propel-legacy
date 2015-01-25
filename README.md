# DeployApp

A simple module to deploy flask application using Gunicorn, Supervisor and NGinx as a proxy

By default, application will be deployed on port 80 with Nginx.

**DeployApp** assign a random proxy for Gunicorn to work

Each application must have its own server name.

It also run scripts on the server and supervisor runners

### Install

	pip install deployapp


### How to use:

##Deploy WebApps

Create a file in your application root directory called: `deployapp.yaml`

Add the following config in there:

    ---
      sites:
        -
          server_name: "myserver.com"
          app: "run_myserver:flask_app"
          static_dir: "myserver/static"


Substitute `myserver.com` with your `site name`

Substitute `run_myserver:flask_app` with your flask app name

Substitute `myserver/static` with your application's static file

Then on the command line:

	deployapp --sites


#### Deploy multiple applications:

    ---
      sites:
        -
          server_name: "myserver.com"
          app: "run_myserver:flask_app"
          static_dir: "myserver/static"
        -
          server_name: "otherserver.com"
          app: "run_otherserver:flask_app"
          static_dir: "otherserver/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80
        -
          server_name: "worker.server.com"
          app: "run_worker_server:flask_app"
          static_dir: "worker_server/static"


This config above will deploy 3 apps.

For custom gunicorn configuration, set the gunicorn (dict) settings

---

##Run Scripts 

Add the following in your deployapp.yaml to run scripts before the deployment of the app.

`scripts` is a **LIST** containing the full path of execution of your scripts

    scripts:
      - "hostname"
      - "ls -l"

So it could look something like this:

    ---
      sites:
        -
          server_name: "myserver.com"
          app: "run_myserver:flask_app"
          static_dir: "myserver/static"
        -
          server_name: "otherserver.com"
          app: "run_otherserver:flask_app"
          static_dir: "otherserver/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80
        -
          server_name: "worker.server.com"
          app: "run_worker_server:flask_app"
          static_dir: "worker_server/static"


    scripts:
      - "hostname"
      - "ls -l"
      
To execute script alone:
	
	deployapp --scripts


## Deploy All

You can deploy and run everything at once:

	deployapp -a 
	
	or 
	
	deployapp --all
	
### Order of execution:

Upon launching `deployapp --all` , it will execute in the following order: 
	
1) scripts

2) sites

---

## Other fun stuff

####Setup A Bare Git Repo

Setup a git repo, which will include a bare repo to push content to, and the actual content directory

    cd /home/mysite
    deployapp --git-init www


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

#### Set/Unset self deploy

You can set it to self deploy on push `--set-self-deploy ${repo}` or unset self deploy if it has been set `--unset-self-deploy ${repo}`


    cd /home/mysite
    deployapp --set-self-deploy www

    # or

    deployapp --unset-self-deploy www

It can be combined with git init

    deployapp --git-init www --set-self-deploy www

---

#### Reload Server

To reload the server

	deployapp -r


####requirements.txt

If a requirements.txt exist, it will run it before deploying



---

### deployapp.yaml:


Inside of the directory that contains the python web app, create a file `deployapp.yaml`

**deployapp.yaml** contains the params to properly deploy your app, run scripts etc

    ---
      sites:
        -
          server_name: "myserver.com"
          app: "run_myserver:flask_app"
          static_dir: "myserver/static"
        -
          server_name: "otherserver.com"
          app: "run_otherserver:flask_app"
          static_dir: "otherserver/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80
        -
          server_name: "worker.server.com"
          app: "run_worker_server:flask_app"
          static_dir: "worker_server/static"
          gunicorn:
              workers: 4
              preload: ""
              port: 80

    scripts:
      - "hostname"
      - "ls -l"

    runners:
      -
         name: ""
         command: ""
         directory: ""
         user: ""
         environment: ""
         remove: False  # Bool



#### Description


	sites: # A list of dict with the following params
       - app string: $module_name:$variable_name. The application to load
       - server_name string: The name of the server ie: mysite.com
       - static_dir string: The static directory relative to
       - gunicorn: dict of gunicorn config (http://docs.gunicorn.org/en/develop/configure.html)
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

- Supervisor
 
- Gunicorn

- Gevent

---

License: MIT - Copyright 2014/2015 Mardix

