from campaign_supervisor.campaign_supervisor import app
from asgiref.wsgi import WsgiToAsgi

asgi_app = WsgiToAsgi(app)
