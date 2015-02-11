# Deployapp

**deployapp** is a package to deploy multiple Python sites/application in virtualenv.  It also allows you to deploy PHP/HTML applications, run scripts and run workers with Supervisor.

The reason for such package, is because I wanted to deploy multiple isolated Flask sites on DigitalOcean, and because Elastic Beanstalk (AWS) was too damn expensive. 

For Python application it uses Virtualenv to isolate each application, Gunicorn+Gevent as the backend server,
Supervisor and Nginx.

For PHP/HTML sites, it just uses the path as it would in normal environment, and you must have php-fpm for Nginx configured already.


Requirements:

    - Nginx

    - Gunicorn

    - Supervisor

    - Gevent

    - Virtualenvwrapper

    - php-fpm (optional if running PHP/HTML site)
    

** TESTED ON CENTOS AND WITH PYTHON 2.7.

---


### Install

	pip install deployapp


After installing *deployapp* for the first time, run the following to setup
Supervisor conf and logs directories compatible to deployapp.

    deployapp-setup

*You may need root admin.

---

### How to use

**deployapp** works in the current working directory (CWD). You must have the file
`deployapp.yml` in order for it to execute properly.

So you must `cd` into the directory that contains your `deployapp.yml`

Let's say my application is as: `/home/myapp.com/www`

	cd /home/myapp.com/www
	
Fron there you can run the commands below:

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


## WEB: Deploy


#### A simple flask app would look something like this:

    virtualenv:
      name: "mynewsite.com"
 
    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"
    
        nginx:
          aliases:
            "/static": "static"
            
For Python application/sites, `virtualenv` is required. 

Upon deploying, it will create the NGINX config file, run Gunicorn+Gevent and the application with Supervisor.

#### A basic PHP/HTML site would have the following structure. PHP-FPM is required.

    web:
      -
        name: "my-php-html-site.com"

For PHP/HTML site we don't need `virtualenv`.        
        
Upon deploying, it will create the NGINX config file and use PHP-FPM.

        
#### Description of the config above

- **virtualenv**: A dict of the virtualenv info. It required for Python application

	- **name**: The name of the virtualenv
	
- **web**: A list of dict website to deploy
	
	- **name**: The website name
	- **application**: The application path in the current directory: 'module:app'
	- **nginx**: A dict of Nginx config
		- **aliases**: A dict of aliases to use in NGINX. The key is the nginx location, the value is the path
			- "/static": "static"
	
**Concerning paths**

By default, all paths are relative to the current directory. So let's say you are under: `/home/myapp.com/www`, setting the aliases: `/static: "static"`, it will automatically add the current directory to the path. The alias will turn into: `/home/myapp.com/www/static`

To use an absolute path, you must prefix the path with a slash `/`. 


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
                       
The above conf, will deploy multiple sites on the same virtualenv. The second 


## WEB: Advanced config

You can add more NGINX and Gunicorn config. Gunicorn config is only for Python app. 

            
    virtualenv:
      name: "mynewsite.com"

    web:
      -
        name: "mynewsite.com"
        application: "run:flask_app"
        remove: False
        exclude: False
        
		# Nginx Config
        nginx:
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
          

          
#### Web Config

- name: (string domain) The site's name

- application: The application to run. It requires virtualenv

- remove: (bool) When True, it will remove the site (config) from the server

- exclude: (bool) When True, it will not try to deploy or re-deploy. 


                      
#### Gunicorn Config

For Gunicorn, the following values are set by default:
 
- workers: (This is calculated based on the total CPU )

- threads: 4

- max-requests: 500

- worker-class: gevent


To disable any of the default values, you can set them as empty or use the desired value

For more config, please refer to: http://docs.gunicorn.org/en/develop/configure.html 

#### NGINX Config

- port: 80

- root_dir: If provided, it will be used as root dir in nginx, when using PHP/HTML site

- logs_dir: If provided, it will be used to save the logs 

- aliases: (dict) location/path pair to create aliases

- force_non_www: (boolean) - If True, it will redirect www to non-www

- force_www: (boolean) - If True, it will redirect non-www to www

- server_directives: (string) Extra directives to include in the server block. 

- ssl_directives: (string) Custom ssl directives to include the server block

- ssl_cert: (string) path to the SSL certificate path. 

- ssl_key: (string) path the the SSL certificate key 

- exclude: (bool)










---
 
### deployapp --git-init $repo_name

To create a bare repo git directory to push content to with `git push`

    cd /home/$mydomain.com
    deployapp --git-init www

It will create 3 directories:

`www` : Where your site content will reside

`www.git` : A git bare repo

`www.logs`: A directory


---

## Learn More

### deploy.yml

**deployapp.yml** is a config file that contains the websites, scripts and workers
to deploy.






License: MIT - Copyright 2015 Mardix

