# Propel

[![Join the chat at https://gitter.im/mardix/deployapp](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/mardix/deployapp?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

### About
 
Propel allows you to deploy multiple Python/PHP/HTML apps (sites) 
on a single server, run scripts and background workers.

#### - Why did I create Propel ?

The main reason, was to deploy multiple Flask apps on a single DigitalOcean VM
 effortlessly. The other reason, was to make it easy to deploy applications. 
 
---

##TLDR; Install and run Propel (simple Flask example)

1. On the server you intend to run your applications, install Propel 
by running the following commands:

         pip install propel
        
         propel-setup
    
    
1. CD in the directory that contains your app, and create the following files:

    -app.py 
    
        from flask import Flask
        
        app = Flask(__name__)
        
        @app.route("/")
        def index():
            return "Hello Propel!"
    
    -requirements.txt
    
        Flask
    
    -propel.yml
    
        virtualenv:
          name: "mysitename.com"
        
        web:
          -
            name: "mysitename.com"
            application: "app:app"
            
1. Inside of your app directory run:

        propel -w mysitename.com
    
1. Now go to `http://mysitename.com`
    
1. Profit! (or your money back)

--- 
 
### Features

#### Deploy Python

Propel allows you deploy multiple Python sites/applications (Flask, Django)
by isolating each app into its own virtualenv, using Virtualenvwrapper, then 
puts it online using Gunicon+Gevent under Supervisor, to make sure it's always up. 
Then uses NGinx as proxy to access the sites.

#### - Deploy PHP/HTML

Propel is not limited to only Python app, it can deploy PHP/HTML sites too 
using PHP-FPM.

#### - Script and Workers

Besides deploying sites/apps. Propel can run scripts before and after deployment.
Run other scripts individually. And background running scripts (workers) with Supervisor. 

#### - Maintenance mode

Propel also has a maintenance mode that will display a maintenance page when the 
website is down for maintenance or is being deployed.


#### - Packages 

Propel makes use of the following packages:

    - Gunicorn

    - Supervisor

    - Gevent

    - Virtualenvwrapper
    
    - PyYaml
    
    - Jinja2
    
(They will be installed automatically, so no need to do it manually)

Requirements:

    - Nginx

    - php-fpm

	- git (not really required, but good to have)
    
---



## Install & Setup

	pip install propel

After installing *propel* for the first time, run the following command to setup 
Supervisor conf and logs directories compatible to propel.

    propel-setup


** You may need root admin

You may also need to install some other packages based on your system.

Once done, you should be good to go.

---

## How to use

**Propel** works in the current working directory (CWD). You must have the file
`propel.yml` in order for it to execute properly.

So you must `cd` into the directory that contains your `propel.yml`

Let's say my application is at: `/home/myapp.com/www`

	cd /home/myapp.com/www
	
From there you can run the commands below:

#### propel --all-webs

To deploy all websites. It will also run scripts.before_web and scripts.after_web

    propel --all-webs


#### propel -w | --webs [site.com, [site...]]

To deploy site by name. It will also run scripts.before_web and scripts.after_web

    propel -w mysite.com mysecondsite.com


    
### propel -s | --scripts [name, [names ...]]

To run a custom script

    propel --scripts my_script_name
    
Run multiple scripts

    propel --scripts my_script_name another_script a_third_script
    
    
#### propel -k | --workers [name, [names ...]]

To run workers in the background using Supervisor

    propel --workers worker_name another_name


### propel -x | --undeploy

To undeploy all. It will remove sites, scripts, workers, and destroy the virtualenv

    propel --undeploy


### propel -m | --maintenance on|off  

(This has been deprecated)

To activate/deactivate the site maintenance page

    propel --maintenance on
    
    propel --maintenance off


### propel -c | --create [name]

To create a new application bare repository ready to push application to. 

    propel -c /home/myapp/myapp
    
    # or
    
    # It will place the repository inside of /home/myapp/myapp
    propel -c /home/myapp/myapp
    
    
### propel -r | --reload

To reload Nginx servers and refresh Supervisors config

    propel --reload

### propel --status

To show the status of all running Propel application. Running applications are active apps on Supervisor.

    propel --status
    
    
### propel --restart

To completely restart all Supervisors processes

    propel --restart
    
---

# propel.yml

`propel.yml` is a config file that tells propel what to deploy and run.

### How does it work ?

## WEB


#### A simple flask app deployment would look something like this:

    virtualenv:
      name: "mynewsite.com"
 
    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"
    
        nginx:
          aliases:
            "/static": "static"
            
**For Python application/sites, `virtualenv` is required. The requirements.txt must also exist to install the necessary packages.  

Upon deploying a Python app, Propel will the following:

- Instantly set the site on maintenance mode. So when a visitor comes, the will a maintenance page 

- create the virtualenv

- install the requirements.txt in the virtualenv

- create a random port and assign it to Gunicorn. By default it will assign `gevent` 
as the worker-class for Gunicorn, set the numbers of workers and threads.

- add the Gunicorn command to Supervisor for process monitoring 

- create the Nginx config file for the site and use it as proxy to point to the Gunicorn instance.

- ... 

- Profit!


#### A basic PHP/HTML site would have the following structure. PHP-FPM is required.

    web:
      -
        name: "my-php-html-site.com"

**For PHP/HTML site we don't need `virtualenv`.        
        
Upon deploying, it will create the NGINX config file and use PHP-FPM.

        
#### Description of the config above

- **virtualenv**: A dict of the virtualenv info. It required for Python application

	- **name**: The name of the virtualenv
	
- **web**: A list of dict website to deploy
	
	- **name**: The website name
	- **application**: The application path in the current directory: 'module:app'. Only for python
	- **nginx**: A dict of Nginx config
		- **aliases**: A dict of aliases to use in NGINX. The key is the nginx location, the value is the path
			- "/static": "my-static"
	
**Concerning paths**

By default, all paths are relative to the current directory. So let's say you are under: `/home/myapp.com/www`, setting the aliases: `/static: "my-static"`, it will automatically add the current directory to the path. The alias will turn into: `/home/myapp.com/www/my-static`

That's how it would be in the Nginx file:

    location /static {
        alias /home/myapp.com/www/my-static
    }
	

** To refer an absolute path, you must prefix the path with a slash `/`


#### Example of multiple sites

The same above, but with multiple sites and multiple aliases

    virtualenv:
      name: "mynewsite.com"

    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"

        nginx:
          aliases:
            "/static": "mytothersite/static"
            "/photos": "mytothersite/photos"

      -
        name: "my-php-html-site.com"
        nginx:
        	root_dir: "html"

            
For the `my-php-html-site.com` the root dir is the `html` directory that's in the current working directory.
                   
                       
The above conf, will deploy multiple sites. The python app will be deployed in the virtualenv, the php/html site will be deployed as is.


## WEB: Advanced config

You can add more NGINX and Gunicorn config. Gunicorn config is only for Python app. 

            
    virtualenv:
      name: "mynewsite.com"
	  rebuild: False
	  directory: ""
	  pip_options: ""
	  
    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"
        remove: False
        exclude: False
        environment: KEY1="value1",KEY2="value2"
        
		# Nginx Config
        nginx:
          server_name: "site1.com admin.site2.com"
          port: 80
          root_dir: ""
          logs_dir: ""
          aliases:
            "/static": "mysite/static"
          force_non_www: True
          force_www: False
          server_directives: ""
          ssl_directives: ""
          ssl_cert: ""
          ssl_key: ""
      
      	# Gunicorn config
        gunicorn:
          workers: 4
          threads: 4
          "max-requests": 100
          
#### Virtualenv config

- name: The name of the virtualenv

- rebuild: (bool) When True, it will rebuild the virtualenv 

- directory: (path) The virtualenvs directory. By default it is set to /root/.virtualenvs 

- pip_options: (string) String of options to pass to pip. ie: --process-dependency-links --upgrade 
          
#### Web config

- name: (string domain) The site's name

- application: The application to run. It requires virtualenv. Python only.

- remove: (bool) When True, it will remove the Nginx config file and stop Supervisor if Python, from the server

- exclude: (bool) When True, it will not try to deploy or re-deploy. It takes precedence over 'remove'. 

- environment: A list of key/value pairs in the form KEY="val",KEY2="val2" that will be placed in the supervisord process’ environment


#### NGINX config

- port: 80 by default

- server_name: (string) Optional if the server name is different than name, or has multiple server_name. Separate multiple server with space 

- root_dir: If provided, it will be used as root dir in nginx, when using PHP/HTML site

- logs_dir: If provided, it will be used to save the logs 

- aliases: (dict) location/path pair to create aliases

- force_non_www: (boolean) - If True, it will redirect www to non-www

- force_www: (boolean) - If True, it will redirect non-www to www

- server_directives: (multi line text) Extra directives to include in the server block. 

- ssl_directives: (multi line text) Custom ssl directives to include the server block

- ssl_cert: (path) path to the SSL certificate path. 

- ssl_key: (path) path the the SSL certificate key 

                 
#### Gunicorn config

For Gunicorn, the following values are set by default:
 
- workers: (This is calculated based on the total CPU )

- threads: 4

- max-requests: 500

- worker-class: gevent


To disable any of the default values, you can set them as empty or use the desired value

For more config, please refer to: http://docs.gunicorn.org/en/develop/configure.html


#### Maintenance config

*Deprecated

The maintenance config allows you to set page to show and turn on/off automatically 

- active: (bool) Turn on/off maintenance page

- page: (path) The maintenance page. If it doesn't exist, it will fallback to the propel default one

- allowed_ips: (list) List of ips to allow. When allowed_ips is available, it will allow the ips to 
access the site, but show the maintenance page to all others. 


---

## SCRIPTS

Propel allows you to run scripts. Scripts can be run as is, or before and after deployment:

Scripts is a dict of with script name to execute. A script can contain multiple commands 

Each command must have the `command` param, and optionally `directory` if the script is not being excuted from the same directory. When `directory` is provided, it will `cd` into it and run the `command`

    scripts:
    
      # Run before all
      before_all: 
        - command: "$PYTHON_ENV myscript.py"
        
      # Run after all
      after_all:
        - command: "$PYTHON_ENV myscript.py"
        
      # run before web deployment
      before_web:
        - command: "$PYTHON_ENV myscript.py"
    
      # run after web deployment
      after_web:
        - command: "$PYTHON_ENV myscript.py"
    
      # run this script when UNDEPLOYING
      undeploy:
        - command: ""
    
      # MY_SCRIPT_NAME: Custom script by name
      my_script_name:
        - 
          command: ""
        -
          directory: ""
          command: "$PYTHON_ENV myscript.py"
          
And to run any of these scripts, you can just do:

    propel -s my_script_name
    
or multiple scripts:
    
    propel -s my_script_name another_script after_all
    
    
#### Scripts command with variables: $PYTHON_ENV and $LOCAL_BIN

As a convenience, there are a few variables to refer to the virtualenv. They allow you to refer to the location without knowing the full path, specially when in virtualenv.

- $PYTHON_ENV: refers to the Python (ie: /root/.virtualenvs/myvirtualenv/local/bin/python2.7)

- $LOCAL_BIN: refers to the local bin like (ie: /root/.virtualenvs/myvirtualenv/local/bin/)

- $CWD: refers to the current working directory

        -
          command: "$PYTHON_ENV manage.py"

The command above will execute the manage.py with the virtualenv python.

**Config description**

- command: (string) (required) the command to use. You can the $PYTHON_ENV and $LOCAL_BIN variables in it.

- directory: (string) The directory the command is being executed at. If empty, it will be executed in the current working directory

- exclude: (bool) When True it will no run or rerun the worker


#### before_all, after_all, before_web, after_web, before_workers, after_workers

Some pre-made hook to run before and after 

`before_all`: Before setting up everything

`after_all`: After setting up everything
 
`before_web`: Before web deployment
 
`after_web`: After web deployment
 
`before_workers`: Before workers deployment
 
`after_workers`: After workers deployment 



    scripts:
        before_all:
          - command: "$PYTHON_ENV myscript.py"
        
        after_all:
          - command: "$PYTHON_ENV another-script.py"
            
        before_web:
          - command: "$PYTHON_ENV myscript.py"
        
        after_web:
          - command: "$PYTHON_ENV another-script.py"
       
        before_workers:
          - command: "$PYTHON_ENV myscript.py"
        
        after_workers:
          - command: "$PYTHON_ENV myscript.py"
    
    
#### UNDEPLOY

`undeploy` will run when undeploying the application. It can be used to clean up etc when removing the site.
ie: `propel --undeploy`

    scripts:
      undeploy:
        - command: "time"
        - command: "rm some_path"
        
        
#### Custom Scripts: $SCRIPT_NAME
    
You can setup your custom scripts to be run manually.

`$script_name` (with $script_name being the name of the script). It will be run when called manually. 

ie: `propel -s setup_cron`

    scripts:
      setup_cron:
        -
          directory: ""
          command: "mysetup_cron_script"

    
---

## WORKERS

Workers (just like Scripts) are scripts to run continuously in the background via `Supervisor`. 

`workers` contains a dict of tasks grouped by name, which contain the work to execute.


      # To run this: propel -k managers
      managers:
        -
          name: "manager1"
          command: "$PYTHON_ENV trigger.py
          environment: ""
    
      # To run this: propel -k jobs
      jobs:
        -
          name: "myworker1"
          command: "$PYTHON_ENV myyworker1.py
          environment: ""
        -
          name: "myworker2"
          directory: ""
          command: "$PYTHON_ENV myyworker2.py"
          environment: ""
          user: ""
          exclude: True  # Prevent this worker from rerunning


**Config description**

- name: (string) (required) The name of the worker

- command: (string) (required) the command to use. You can the $PYTHON_ENV and $LOCAL_BIN variables in it.

- directory: (string) The directory the command is being executed at. If empty, it will be executed in the current working directory

- user: (string) The user 

- environment: (string) Environment string

- exclude: (bool) When True it will no run or rerun the worker. It takes precedence over 'remove'. 

- remove: (bool) When True it will remove the worker from the script

---

## MAINTENANCE

Propel allows you to set your site on Maintenance mode. When visitors come to the site, they will be
greeted with a maintenance page to tell them the site is under maintenance. 

To manually set the site under maintenance

    propel --maintenance on 
    
    // or 
    
    propel -m on
    
And to remove it

    propel --maintenance off
    
    // or 
    
    propel -m off

Propel already has a default page that it will render upon being under maintenance.


#### Set the maintenance in propel.yml

You can also set the maintenance mode in the `propel.yml`. This way it will turn on/off maintenance each time 
you run `propel -w`

Edit your `propel.yml` and add the line below.

    maintenance:
      active: True 
     
      
#### Set a custom maintenance page

To set your custom maintenance page, add the `page` under maintenance. The page must be relative to the site's root
      
    maintenance:
      active: True  
      page: "maintenance/index.html" 

So if your site is at: /home/mysite.com, the maintenance page is at: /home/mysite.com/maintenance/index.html


#### Put site under maintenance, but give full access to certain ips

Sometimes, even if the site is under maintenance, you would like to check everything on it to make sure it works 
before activate it back again; or you would want to give certain people access before going live.

To do so, Propel allows to set a list of ips you would like to give access while the site is under maintenance

    maintenance:
      active: True
      allow_ips: # List of ips to allow to view the site
        - 1.2.4.5
        - 2.3.4.5
        
#### Deactivate Maintenance Mode

To deactivate and put the full site back online

    maintenance:
      active: False

If the site is under maintenance using propel.yml, `propel -m off` will not turn off maintenance. 
You must deactivate it in propel.yml


---
---
 
 
## Some Xtra

 
### propel --git-init $repo_name 

To create a `git bare repo` directory to push content to with `git push`

    cd /home/mydomain.com
    
    propel --git-init www
    

It will create 3 directories:

`www` : Where your application content will reside

`www.git` : A git bare repo

`www.logs`: A logs directory


So your git path to push directly could be:

    ssh://my.ip.address/home/mydomain/www.git

    
And when you `git push` it will update the `/home/mydomain/www` directory


### propel --git-push-web $repo_name 

It will add the command `propel -w` in the *post-receive* hook file so it redeploy the app on each push. Good for Python app. 

    cd /home/mydomain.com
    
    propel --git-push-web www
    
    
### propel --git-push-cmd $repo_name  [cmd, [cmd...]]
    
To add custom command to be executed after a git push

    cd /home/mydomain.com
    
    propel --git-push-cmd www 'ls -l' 'cd /' ''


---

Thank you 

Mardix :) 

---

License: MIT - Copyright 2015 - 2017 Mardix

