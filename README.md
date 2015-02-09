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
    

** TESTED ON CENTOS AND WITH PYTHON 2.7

---

### Install

	pip install deployapp


After installing *deployapp* for the first time, run the following to setup
Supervisor conf and logs path compatible to deployapp.

    deployapp-setup-supervisor

*You may need root admin.

---

### Quick Examples

**deployapp** works in the current working directory (CWD). You must have the file
`deployapp.yml` in order for it to execute properly.


#### deployapp -w | --websites

To deploy websites. It will also run scripts_pre_web and scripts_post_web

    cd $APPLICATION_ROOT_DIR
    deployapp -w


#### deployapp --scripts

To run scripts

    cd $APPLICATION_ROOT_DIR
    deployapp --scripts

#### deployapp --workers

To run workers in the background using supervisor

    cd $APPLICATION_ROOT_DIR
    deployapp --scripts


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


[in construction]



License: MIT - Copyright 2015 Mardix

