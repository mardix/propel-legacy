# Deploy-WebApp

A module to deploy python web app (ie: flask) using Gunicorn and Supervisor on Nginx.
Celery is also added as a bonus, but you must 'pip install celery' fisrt.

By default, application will be deployed on port 80 with Nginx. Each application must have its own server name.


### Install

	pip install deploy-webapp


### How to use:

To deploy

	cd /home/mysite/wwww
	deploy-webapp -d
	
To reload the server

	deploy-webapp -r
	
	
### Setup & deploy_webapp.json:
	
Inside of the directory that contains the python web app, create a file `deploy_webapp.json`


**deploy_webapp.json** contains the params to properly deploy your app


    {
        "deploy": [
            {
                "server_name": "myserver.com",
                "app": "run_myserver:flask_app",
                "static_dir": "myserver/static"
            },
            {
                "server_name": "otherserver.com",
                "app": "run_otherserver:flask_app",
                "static_dir": "otherserver/static",
                "port": 80,
                "gunicorn_workers": 4
            },
            {
                "server_name": "worker.server.com",
                "app": "run_worker_server:flask_app",
                "static_dir": "worker_server/static",
                "port": 80,
                "gunicorn_workers": 4,
                "celery": True
            }
        ],

        "undeploy": [
            {
                "server_name": "my_old_server.com",
                "app": "old_server:flask_app"
            }
        ]

    }



#### deploy_webapp.json params


	deploy:
       - app string: $module_name:$variable_name. The application to load
       - server_name string: The name of the server ie: mysite.com
       - static_dir string: The static directory relative to
       - port int : The nginx port to run on. By default: 80
       - celery bool: To setup the app as a celery app - default false
       - gunicorn_workers int: the total workers for gunicro

	undeploy:
       - app string: $module_name:$variable_name. The application to load
       - server_name string: The name of the server ie: mysite.com


####requirements.txt

If a requirements.txt exist, it will run it before deploying


---

### Requirements

- NGinx

- Supervisor
 
- Gunicorn

- Celery (Optional, must `pip install celery`)
---

License: MIT - Copyright 2014 Mardix