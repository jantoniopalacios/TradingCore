from setuptools import setup, find_packages

setup(
    # Nombre del paquete (lo que vas a importar: from trading_engine import ...)
    name='trading_engine',
    
    # Versión de tu motor.
    version='0.1.0',
    
    # Especifica que el código fuente está en la carpeta 'src'
    package_dir={'': 'src'},
    
    # Encuentra automáticamente todos los subpaquetes (core, utils, indicators)
    # dentro del directorio 'src'
    packages=find_packages(where='src'),
    
    # Lista de dependencias 
    install_requires=[
        'numpy',
        'pandas',
        'yfinance',
        'alpha_vantage',
        'ta', # Technical Analysis library
        'backtesting', # Core backtesting dependency
        'matplotlib', # For charting (often used by trading logic)
        'bokeh', # Also often used for charting
        'contourpy', 
        'cycler',
        'fonttools',
        'kiwisolver',
        'pyparsing',
        'python-dateutil',
        'pytz',
        'tzdata',
        'six',
        'requests',
        'urllib3',
        'charset-normalizer',
        'idna',
        'multitasking',
        'narwhals',
        'peewee',
        'pillow',
        'xyzservices',
        # Si usas aiohttp/yarl en Data_download:
        'aiohttp', 'aiosignal', 'frozendict', 'frozenlist', 'multidict', 'yarl',
        # Si se usan para web scraping en Data_download
        'beautifulsoup4', 'soupsieve', 
        # Si se usan para cargar configuraciones
        'PyYAML', 'python-dotenv', 
    ],
    
    # Metadatos (Opcional, pero recomendado)
    author='Tu Nombre',
    description='Motor de Backtesting y Utilidades de Trading.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tu-usuario/Trading', 
)