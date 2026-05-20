def create_app(user_mode="admin"):
    app = Flask(__name__)
    
    # Configuración básica
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = ENGINE_OPTIONS.copy()
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_TradingCore")
    app.config['USER_MODE'] = user_mode

    setup_logging(app)
    db.init_app(app)

    # REGISTRAR BLUEPRINT PRIMERO (FUERA de app_context)
    try:
        from .routes.main_bp import main_bp 
        app.register_blueprint(main_bp)
        app.logger.info("✓ Blueprint main_bp registrado exitosamente")
    except Exception as e:
        app.logger.error(f"ERROR registrando blueprint: {e}")
        sys.exit(1)

    # LUEGO: Operaciones que REQUIEREN app_context (BD, config)
    with app.app_context():
        try:
            from .database import Usuario 
            from .configuracion import cargar_y_asignar_configuracion
            
            db.create_all()
            app.logger.info(f"Cargando parámetros para {user_mode}...")
            try:
                config_data = cargar_y_asignar_configuracion(user_mode)
                app.config.update(config_data)
            except Exception as e_cfg:
                app.logger.warning(f"No se pudo cargar configuración de BD al iniciar: {e_cfg}")
            
        except Exception as e:
            app.logger.error(f"ERROR en app_context: {e}")
            sys.exit(1)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

    return app
