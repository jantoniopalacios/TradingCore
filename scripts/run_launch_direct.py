from pathlib import Path
import sys
project_root = Path(__file__).parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion
from scenarios.BacktestWeb.routes.main_bp import run_backtest_and_save

app = create_app(user_mode='admin')

with app.app_context():
    try:
        # Prepare config for admin
        base_config = cargar_y_asignar_configuracion('admin')
        base_config['user_mode'] = 'admin'
        # Try to get user id if available
        try:
            from scenarios.BacktestWeb.database import Usuario
            u = Usuario.query.filter_by(username='admin').first()
            base_config['user_id'] = u.id if u else None
        except Exception:
            base_config['user_id'] = None

        print('Launching run_backtest_and_save directly (this may take a while).')
        run_backtest_and_save(app, base_config, 'admin')
        print('Direct run complete.')
    except Exception as e:
        print('Error running direct launch:', e)
