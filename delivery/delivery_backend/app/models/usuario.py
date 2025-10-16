from flask_login import UserMixin

class Usuario(UserMixin):
    def __init__(self, id, email, tipo, id_restaurante=None):
        self.id = id  # obrigatório para flask-login
        self.email = email
        self.tipo = tipo  # cliente ou restaurante
        self.id_restaurante = id_restaurante  # aqui guardamos o restaurante