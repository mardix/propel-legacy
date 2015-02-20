# Deployapp

**Deployapp** is a package to deploy multiple Python sites/application in virtualenv.  It also allows you to deploy PHP/HTML applications, run scripts and run workers with Supervisor.

For Python applications it uses Virtualenv to isolate each application, Gunicorn+Gevent as the backend server, Supervisor to monitor it and Nginx as proxy.

For PHP/HTML sites, it just uses the path as it would in normal environment, and you must have php-fpm for Nginx configured already.


West Side Story: I created this package because I wanted to deploy multiple isolated Flask sites on DigitalOcean. And I wanted something that automates the deployment process of my sites, while sipping on some Caramel Iced Coffee :) 


Deployapp makes use of the following packages:

    - Gunicorn

    - Supervisor

    - Gevent

    - Virtualenvwrapper
    
    - PyYaml
    
    - Jinja2
    

Requirements:

    - Nginx

    - php-fpm (optional if running PHP/HTML site)

	- git (not really required, but good to have)


    
---


## Install & Setup

	pip install deployapp

After installing *deployapp* for the first time, run the following command to setup Supervisor conf and logs directories compatible to deployapp.

    deployapp-setup


One more thing you may need to do, is add the `virtualenvwrapper` in your `.bashrc`:

    export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python2.7
    source /usr/local/bin/virtualenvwrapper.sh

** of course use the right Python version of your environment

** You may need root admin

Once done, you should be good to go.

---

## How to use

**Deployapp** works in the current working directory (CWD). You must have the file
`deployapp.yml` in order for it to execute properly.

So you must `cd` into the directory that contains your `deployapp.yml`

Let's say my application is at: `/home/myapp.com/www`

	cd /home/myapp.com/www
	
From there you can run the commands below:

#### deployapp -w | --websites

To deploy websites. It will also run scripts_pre_web and scripts_post_web

    deployapp -w


#### deployapp --scripts

To run scripts

    deployapp --scripts

#### deployapp --workers

To run workers in the background using Supervisor

    deployapp --scripts

---

# deployapp.yml

`deployapp.yml` is a config file that tells deployapp what to deploy and run.

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

Upon deploying a Python app, Deployapp will the following:

- create the virtualenv

- install the requirements.txt in the virtualenv

- create a random port and assign it to Gunicorn. By default it will assign `gevent` as the worker-class for Gunicorn, set the numbers of workers and threads.

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
	  
    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"
        remove: False
        exclude: False
        
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


          
#### Web config

- name: (string domain) The site's name

- application: The application to run. It requires virtualenv. Python only.

- remove: (bool) When True, it will remove the Nginx config file and stop Supervisor if Python, from the server

- exclude: (bool) When True, it will not try to deploy or re-deploy. 


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



---

## SCRIPTS

Deployapp allows you to run scripts. Scripts can be run as is, or before and after deployment:

Scripts is a list of dict of scripts to run. It must have the `command` param, and optionally `directory` if the script is not being excuted from the same directory. When `directory` is provided, it will `cd` into it and run the `command`

    scripts:
      -
        command: "uname"
      -
        command: "ls -l"
        directory: "/my-directory"        


#### Scripts command with variables: $PYTHON and $LOCAL_BIN

As a convenience, there are a few variables to refer to the virtualenv. They allow you to refer to the location without knowing the full path, specially when in virtualenv.

- $PYTHON: refers to the Python (ie: /root/.virtualenvs/myvirtualenv/local/bin/python2.7)

- $LOCAL_BIN: refers to the local bin like (ie: /root/.virtualenvs/myvirtualenv/local/bin/)


      scripts:
        -
          command: "$PYTHON manage.py"

The command above will execute the manage.py with the virtualenv python.

**Config description**

- command: (string) (required) the command to use. You can the $PYTHON and $LOCAL_BIN variables in it.

- directory: (string) The directory the command is being executed at. If empty, it will be executed in the current working directory

- exclude: (bool) When True it will no run or rerun the worker


#### SCRIPTS_PRE_WEB & SCRIPTS_POST_WEB

`scripts_pre_web` and `scripts_post_web` are ran before and after web deployment respectively, and follow the same rules as SCRIPTS above.


    scripts_pre_web:
      -
        command: "$PYTHON myscript.py"
    
    scripts_post_web:
      -
        command: "$PTHON another-script.py"
        
---

## WORKERS

Workers are scripts that are run continuously in the background and are monitored by `Supervisor`. Workers can perform whatever task you assign them to do. 

`workers` is a list of dict of command to run with Supervisor.


    workers:
      - 
        name: "myworkername"
        command: "$PYTHON myworker.py"
      -
        name: "anotherworker"
        directory: ""
        command: "$PYTHONX myotherworker.py"
        user: "www-data"
        environement: ""
        exclude: True 

**Config description**

- name: (string) (required) The name of the worker

- command: (string) (required) the command to use. You can the $PYTHON and $LOCAL_BIN variables in it.

- directory: (string) The directory the command is being executed at. If empty, it will be executed in the current working directory

- user: (string) The user 

- environment: (string) Environment string

- exclude: (bool) When True it will no run or rerun the worker

- remove: (bool) When True it will remove the worker from the script


---
---
 
 
## Some Goodies

 
### deployapp --git-init $repo_name

To create a `git bare repo` directory to push content to with `git push`

    cd /home/mydomain.com
    
    deployapp --git-init www
    

It will create 3 directories:

`www` : Where your application content will reside

`www.git` : A git bare repo

`www.logs`: A logs directory


So your git path to push directly coul be:

    ssh://my.ip.address/home/mydomain/www.git
    

And when you `git push` it will update the `/home/mydomain/www` directory


### deployapp --git-self-deploy $repo_name

It will add the command `deployapp -w` in the *post-receive* hook file so it redeploy the app on each push. Good for Python app. 

### deployapp --git-no-self-deploy $repo_name

It will not auto deploy when you push to the directory.

---

Thank you 

Mardix :) 

---

License: MIT - Copyright 2015 Mardix

