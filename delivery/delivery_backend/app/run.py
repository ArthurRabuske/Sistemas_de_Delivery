from flask import Flask, render_template
from routes.home import home_route
from flask_login import LoginManager
from routes.registro import registro_bp
from routes.login import login_bp
from routes.restaurante import restaurante_bp
import config
from routes.consumidor import consumidor_bp
app = Flask(__name__, template_folder="templates")
app.config.from_object(config)
app.secret_key = app.config.get("SECRET_KEY")  

# === Flask-Login Config ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home.login_register"  # rota de login (ajuste se o seu blueprint for diferente)

# import do modelo de usuário
from models.usuario import Usuario
from utils.database import get_connection

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, email FROM cliente WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    tipo = "cliente"

    if not user:
        cursor.execute("SELECT id, nome as email FROM restaurante WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        tipo = "restaurante"

    cursor.close()
    conn.close()

    if user:
        return Usuario(user["id"], user["email"], tipo)
    return None

# === Registro dos Blueprints ===
app.register_blueprint(home_route)
app.register_blueprint(registro_bp)
app.register_blueprint(login_bp)
app.register_blueprint(restaurante_bp)
app.register_blueprint(consumidor_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)