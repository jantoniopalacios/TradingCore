#!/usr/bin/env python3
"""Fix app.py to move blueprint registration outside app_context"""

with open('scenarios/BacktestWeb/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Section to find
old_section = '''    # 2. CARGA DE MÓDULOS DENTRO DEL CONTEXTO
    with app.app_context():
        try:
            # Importamos aquí para romper el ciclo de importación
            from .database import Usuario 
            from .configuracion import cargar_y_asignar_configuracion
            from .routes.main_bp import main_bp 
            
            db.create_all()
            
            # Registramos rutas
            app.register_blueprint(main_bp)'''

# Replacement section
new_section = '''    # REGISTRAR BLUEPRINT PRIMERO (FUERA de app_context)
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
            
            db.create_all()'''

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('scenarios/BacktestWeb/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ app.py actualizado correctamente - Blueprint movido fuera de app_context")
else:
    print("✗ Sección no encontrada exactamente. Intentando búsqueda alternativa...")
    if 'register_blueprint(main_bp)' in content:
        print("✓ Se encontró register_blueprint, pero formato diferente")
        print("Necesitaremos edición manual")
